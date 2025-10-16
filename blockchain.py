import subprocess
import json
import os
from pymongo import MongoClient

FABRIC_PATH = os.path.expanduser('~/blockchain-voting/fabric-samples/test-network')
CHAINCODE_NAME = 'voting'
CHANNEL_NAME = 'mychannel'

class BlockchainClient:
    """Blockchain client for Hyperledger Fabric voting system"""
    
    def _init_(self):
        self.fabric_path = FABRIC_PATH
        self.chaincode_name = CHAINCODE_NAME
        self.channel_name = CHANNEL_NAME
        
    def _execute_peer_command(self, command_type, function, args=[]):
        """Execute peer chaincode commands"""
        try:
            original_dir = os.getcwd()
            os.chdir(self.fabric_path)
            
            env = os.environ.copy()
            env['PATH'] = f"{self.fabric_path}/../bin:" + env.get('PATH', '')
            env['FABRIC_CFG_PATH'] = f'{self.fabric_path}/../config/'
            env['CORE_PEER_TLS_ENABLED'] = 'true'
            env['CORE_PEER_LOCALMSPID'] = 'Org1MSP'
            env['CORE_PEER_TLS_ROOTCERT_FILE'] = f'{self.fabric_path}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt'
            env['CORE_PEER_MSPCONFIGPATH'] = f'{self.fabric_path}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp'
            env['CORE_PEER_ADDRESS'] = 'localhost:7051'
            
            if command_type == 'invoke':
                cmd = [
                    'peer', 'chaincode', 'invoke',
                    '-o', 'localhost:7050',
                    '--ordererTLSHostnameOverride', 'orderer.example.com',
                    '--tls',
                    '--cafile', f'{self.fabric_path}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem',
                    '-C', self.channel_name,
                    '-n', self.chaincode_name,
                    '--peerAddresses', 'localhost:7051',
                    '--tlsRootCertFiles', f'{self.fabric_path}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt',
                    '--peerAddresses', 'localhost:9051',
                    '--tlsRootCertFiles', f'{self.fabric_path}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt',
                    '-c', json.dumps({"function": function, "Args": args})
                ]
            else:
                cmd = [
                    'peer', 'chaincode', 'query',
                    '-C', self.channel_name,
                    '-n', self.chaincode_name,
                    '-c', json.dumps({"function": function, "Args": args})
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
            os.chdir(original_dir)
            
            return result
            
        except Exception as e:
            os.chdir(original_dir)
            raise e
        
    def submit_vote(self, voter_id, candidate):
        """Submit a vote to the blockchain"""
        try:
            print(f"Submitting vote to blockchain: {voter_id} -> {candidate}")
            
            result = self._execute_peer_command('invoke', 'submitVote', [voter_id, candidate])
            
            if result.returncode == 0:
                print(f"✅ Vote submitted to blockchain successfully!")
                return {'success': True, 'message': 'Vote submitted to blockchain'}
            else:
                print(f"❌ Blockchain submission failed: {result.stderr}")
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            print(f"❌ Blockchain error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_results(self):
        """Get voting results from blockchain"""
        try:
            print("Querying results from blockchain...")
            
            result = self._execute_peer_command('query', 'getResults', [])
            
            if result.returncode == 0:
                results = json.loads(result.stdout.strip())
                print(f"✅ Blockchain results: {results}")
                return results
            else:
                print(f"❌ Blockchain query failed, using MongoDB fallback")
                return self.get_results_from_mongodb()
                
        except Exception as e:
            print(f"❌ Blockchain error: {str(e)}, using MongoDB fallback")
            return self.get_results_from_mongodb()
    
    def get_results_from_mongodb(self):
        """Fallback: Get results from MongoDB"""
        try:
            client = MongoClient('mongodb://localhost:27017/')
            db = client['voting_system']
            votes_collection = db.votes
            
            results = {}
            all_votes = votes_collection.find()
            
            for vote in all_votes:
                candidate = vote.get('candidate')
                if candidate:
                    results[candidate] = results.get(candidate, 0) + 1
            
            print(f"📊 MongoDB Results: {results}")
            return results
            
        except Exception as e:
            print(f"Error getting results from MongoDB: {str(e)}")
            return {}
    
    def check_network_status(self):
        """Check if Hyperledger Fabric network is running"""
        try:
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            
            if 'peer' in result.stdout and 'orderer' in result.stdout:
                return {'status': 'running', 'message': '✅ Blockchain network is running'}
            else:
                return {'status': 'stopped', 'message': '❌ Blockchain network is not running'}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
