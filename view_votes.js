from app.blockchain import BlockchainClient
import json

bc = BlockchainClient()

print("=" * 60)
print("BLOCKCHAIN VOTING RECORDS")
print("=" * 60)

# Get all votes
try:
    result = bc._execute_peer_command('query', 'getAllVotes', [])
    
    if result.returncode == 0:
        votes = json.loads(result.stdout.strip())
        
        if votes:
            print(f"\nTotal Votes Cast: {len(votes)}\n")
            
            for i, vote in enumerate(votes, 1):
                print(f"Vote #{i}:")
                print(f"  Voter ID: {vote.get('voterID')}")
                print(f"  Candidate: {vote.get('candidate')}")
                print(f"  Transaction ID: {vote.get('txId')}")
                print(f"  Document Type: {vote.get('docType')}")
                print("-" * 40)
        else:
            print("\nNo votes found in blockchain.")
    else:
        print(f"Error: {result.stderr}")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("CURRENT RESULTS")
print("=" * 60)

results = bc.get_results()
print(json.dumps(results, indent=2))
