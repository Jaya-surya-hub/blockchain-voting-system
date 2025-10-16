from flask import render_template, request, jsonify, session, redirect, url_for
from app.blockchain import BlockchainClient
from app.security import SecurityHelper
from app.consensus import HybridConsensus
from pymongo import MongoClient
import face_recognition
import numpy as np
import base64
import io
from PIL import Image
import uuid
from datetime import datetime
import json

# Get app from _init_
from app import app

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['voting_system']
users = db.users
votes = db.votes
system_config = db.system_config  # New collection for system settings

# Blockchain client
blockchain_client = BlockchainClient()

# Hybrid Consensus
hybrid_consensus = HybridConsensus()

@app.route('/')
def index():
    return render_template('registration.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        
        # Decode face image
        face_image = data.get('face_image')
        if not face_image:
            return jsonify({'error': 'No face image provided'}), 400
        
        # Remove data URL prefix
        face_data = face_image.split(',')[1] if ',' in face_image else face_image
        face_bytes = base64.b64decode(face_data)
        face_img = Image.open(io.BytesIO(face_bytes))
        face_array = np.array(face_img)
        
        # Get face encoding
        face_locations = face_recognition.face_locations(face_array)
        if not face_locations:
            return jsonify({'error': 'No face detected'}), 400
        
        face_encodings = face_recognition.face_encodings(face_array, face_locations)
        if not face_encodings:
            return jsonify({'error': 'Could not encode face'}), 400
        
        new_face_encoding = face_encodings[0].tolist()
        
        # Check for duplicate face (Ghost voting prevention)
        all_users = list(users.find())
        is_duplicate, matched_voter_id = SecurityHelper.check_duplicate_face(
            new_face_encoding, 
            all_users
        )
        
        if is_duplicate:
            return jsonify({
                'error': f'This face is already registered! Voter ID: {matched_voter_id}. Ghost voting prevented!'
            }), 409
        
        # Encrypt personal data
        encrypted_name = SecurityHelper.encrypt_data(data['name'])
        encrypted_email = SecurityHelper.encrypt_data(data['email'])
        encrypted_phone = SecurityHelper.encrypt_data(data['phone'])
        encrypted_address = SecurityHelper.encrypt_data(data['address'])
        
        # Generate voter ID
        voter_id = str(uuid.uuid4())[:8]
        
        # Create user data with encrypted fields
        user_data = {
            'voter_id': voter_id,
            'name': encrypted_name,
            'email': encrypted_email,
            'phone': encrypted_phone,
            'address': encrypted_address,
            'face_encoding': new_face_encoding,
            'has_voted': False,
            'created_at': datetime.now()
        }
        
        # Save to MongoDB
        users.insert_one(user_data)
        
        print(f"✅ New voter registered with encrypted data: {voter_id}")
        
        return jsonify({
            'message': 'Registration successful! Personal data encrypted.',
            'voter_id': voter_id
        })
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        voter_id = data.get('voter_id')
        face_image = data.get('face_image')
        
        if not voter_id or not face_image:
            return jsonify({'error': 'Missing voter ID or face image'}), 400
        
        # Get user from database
        user = users.find_one({'voter_id': voter_id})
        
        if not user:
            return jsonify({'error': 'Voter not found'}), 404
        
        # REMOVED: Don't block login if already voted - let them access dashboard
        # if user.get('has_voted'):
        #     return jsonify({'error': 'You have already voted'}), 403
        
        # Decode face image
        try:
            face_data = face_image.split(',')[1] if ',' in face_image else face_image
            face_bytes = base64.b64decode(face_data)
            face_img = Image.open(io.BytesIO(face_bytes))
            face_array = np.array(face_img)
            
            # Get face encoding from captured image
            face_locations = face_recognition.face_locations(face_array)
            
            if not face_locations:
                return jsonify({'error': 'No face detected. Please try again.'}), 400
            
            face_encodings = face_recognition.face_encodings(face_array, face_locations)
            
            if not face_encodings:
                return jsonify({'error': 'Could not encode face. Please try again.'}), 400
            
            live_encoding = face_encodings[0]
            
            # Get stored face encoding
            stored_encoding = np.array(user.get('face_encoding'))
            
            # Compare faces
            matches = face_recognition.compare_faces([stored_encoding], live_encoding, tolerance=0.6)
            
            if not matches[0]:
                return jsonify({'error': 'Face verification failed. Please try again.'}), 401
            
            # Decrypt name for display
            decrypted_name = SecurityHelper.decrypt_data(user.get('name'))
            
            # Face verified! Create session
            session['user'] = voter_id
            session['voter_id'] = voter_id
            session['name'] = decrypted_name
            session['token'] = voter_id
            
            print(f"✅ Login successful: {voter_id} (Already voted: {user.get('has_voted', False)})")
            
            return jsonify({
                'success': True,
                'token': voter_id,
                'name': decrypted_name,
                'has_voted': user.get('has_voted', False)  # Send voting status
            }), 200
            
        except Exception as e:
            print(f"Face verification error: {str(e)}")
            return jsonify({'error': f'Face verification error: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# NEW ROUTE: Voter Dashboard
@app.route('/dashboard')
def dashboard():
    if 'token' not in session:
        return redirect(url_for('login_page'))
    return render_template('voter_dashboard.html')

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if request.method == 'GET':
        # Check if user is logged in
        if 'token' not in session:
            return redirect(url_for('login_page'))
        return render_template('voting.html')
    
    # Handle POST (casting vote)
    try:
        data = request.json
        
        # Verify token
        if session.get('token') != data.get('token'):
            return jsonify({'error': 'Invalid token'}), 401
        
        voter_id = session.get('voter_id')
        if not voter_id:
            return jsonify({'error': 'No voter session'}), 401
        
        candidate = data.get('candidate')
        if not candidate:
            return jsonify({'error': 'No candidate selected'}), 400
        
        # Check if already voted
        if votes.find_one({'voter_id': voter_id}):
            return jsonify({'error': 'You have already voted'}), 403
        
        # HYBRID CONSENSUS VALIDATION (PoS + PBFT + Raft)
        print(f"\n🔄 Starting Hybrid Consensus for voter: {voter_id}")
        consensus_result = hybrid_consensus.hybrid_consensus_validate({
            'voter_id': voter_id,
            'candidate': candidate
        })
        
        # Check if consensus approved
        if consensus_result['final_status'] != 'APPROVED':
            print(f"❌ Consensus rejected vote from {voter_id}")
            return jsonify({
                'error': 'Vote rejected by consensus mechanism',
                'details': consensus_result
            }), 403
        
        print(f"✅ Hybrid Consensus approved vote: {voter_id}")
        
        # ElGamal Encryption + Zero-Knowledge Proof
        encrypted_vote = SecurityHelper.elgamal_encrypt_vote(candidate)
        zkp = SecurityHelper.generate_zkp(voter_id, candidate)
        
        print(f"🔐 Vote encrypted with ElGamal: {voter_id}")
        print(f"🔐 ZKP generated: {zkp['commitment'][:16]}...")
        
        # Store vote in MongoDB with encryption AND consensus proof
        vote_data = {
            'vote_id': str(uuid.uuid4()),
            'voter_id': voter_id,
            'candidate': candidate,
            'encrypted_vote': json.dumps(encrypted_vote),
            'zkp': json.dumps(zkp),
            'consensus_proof': json.dumps(consensus_result),
            'timestamp': datetime.now()
        }
        
        votes.insert_one(vote_data)
        
        # Submit to blockchain (Raft ordering)
        try:
            blockchain_result = blockchain_client.submit_vote(voter_id, candidate)
            print(f"🔗 Blockchain (Raft) result: {blockchain_result}")
        except Exception as e:
            print(f"⚠  Blockchain submission failed: {e}")
        
        # Mark user as voted
        users.update_one(
            {'voter_id': voter_id},
            {'$set': {'has_voted': True}}
        )
        
        # Clear session
        session.pop('token', None)
        
        print(f"✅ Vote cast successfully with Hybrid Consensus + Encryption + ZKP: {voter_id}")
        
        return jsonify({
            'message': 'Vote cast successfully with Hybrid Consensus!', 
            'success': True,
            'consensus_type': consensus_result['consensus_type'],
            'validators_used': len(consensus_result['pos_validators'])
        })
    except Exception as e:
        print(f"❌ Vote error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/voting_page')
def voting_page():
    if 'token' not in session:
        return redirect(url_for('login_page'))
    return render_template('voting.html')

@app.route('/results')
def get_results():
    try:
        bc = BlockchainClient()
        results = bc.get_results()
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# NEW ROUTE: Check if results are declared
@app.route('/check_results_status')
def check_results_status():
    try:
        config = system_config.find_one({'key': 'results_declared'})
        if config and config.get('value') == True:
            return jsonify({
                'declared': True,
                'declared_at': config.get('declared_at', 'Unknown')
            })
        else:
            return jsonify({'declared': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# NEW ROUTE: Election Commission Page
@app.route('/election_commission')
def election_commission():
    return render_template('election_commission.html')

# NEW ROUTE: Declare Results (Election Commission)
@app.route('/declare_results', methods=['POST'])
def declare_results():
    try:
        # Update system config to mark results as declared
        system_config.update_one(
            {'key': 'results_declared'},
            {
                '$set': {
                    'key': 'results_declared',
                    'value': True,
                    'declared_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            },
            upsert=True
        )
        
        print("✅ Results declared by Election Commission")
        
        return jsonify({
            'success': True,
            'message': 'Results declared successfully'
        })
    except Exception as e:
        print(f"❌ Error declaring results: {str(e)}")
        return jsonify({'error': str(e)}), 500

# NEW ROUTE: Undeclare Results (For testing/admin)
@app.route('/undeclare_results', methods=['POST'])
def undeclare_results():
    try:
        system_config.update_one(
            {'key': 'results_declared'},
            {
                '$set': {
                    'key': 'results_declared',
                    'value': False
                }
            },
            upsert=True
        )
        
        print("✅ Results undeclared")
        
        return jsonify({
            'success': True,
            'message': 'Results undeclared successfully'
        })
    except Exception as e:
        print(f"❌ Error undeclaring results: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/consensus-stats')
def consensus_stats():
    """API endpoint to view consensus statistics"""
    try:
        stats = hybrid_consensus.get_validator_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
