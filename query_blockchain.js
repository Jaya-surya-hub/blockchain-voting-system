const { execSync } = require('child_process');
const path = require('path');

const FABRIC_PATH = path.join(process.env.HOME, 'blockchain-voting/fabric-samples/test-network');
const CHANNEL_NAME = 'mychannel';
const CHAINCODE_NAME = 'voting';

// Set environment variables
process.env.PATH = ${FABRIC_PATH}/../bin:${process.env.PATH};
process.env.FABRIC_CFG_PATH = ${FABRIC_PATH}/../config/;
process.env.CORE_PEER_TLS_ENABLED = 'true';
process.env.CORE_PEER_LOCALMSPID = 'Org1MSP';
process.env.CORE_PEER_TLS_ROOTCERT_FILE = ${FABRIC_PATH}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt;
process.env.CORE_PEER_MSPCONFIGPATH = ${FABRIC_PATH}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp;
process.env.CORE_PEER_ADDRESS = 'localhost:7051';

function queryBlockchain(functionName, args = []) {
    try {
        const argsStr = JSON.stringify({ function: functionName, Args: args });
        const cmd = peer chaincode query -C ${CHANNEL_NAME} -n ${CHAINCODE_NAME} -c '${argsStr}';
        
        const result = execSync(cmd, { 
            cwd: FABRIC_PATH,
            encoding: 'utf8' 
        });
        
        return JSON.parse(result);
    } catch (error) {
        console.error('Error querying blockchain:', error.message);
        return null;
    }
}

function displayVotes() {
    console.log('='.repeat(70));
    console.log('BLOCKCHAIN VOTING SYSTEM - QUERY RESULTS');
    console.log('='.repeat(70));
    console.log();

    // Get all votes
    console.log('📊 Fetching all votes from blockchain...\n');
    const allVotes = queryBlockchain('getAllVotes');
    
    if (allVotes && allVotes.length > 0) {
        console.log(Total Votes Stored in Blockchain: ${allVotes.length}\n);
        
        allVotes.forEach((vote, index) => {
            if (vote.voterID) {  // Filter out the count object
                console.log(Vote #${index}:);
                console.log(`  Voter ID:       ${vote.voterID}`);
                console.log(`  Candidate:      ${vote.candidate}`);
                console.log(`  Transaction ID: ${vote.txId}`);
                console.log(`  Document Type:  ${vote.docType}`);
                console.log('-'.repeat(70));
            }
        });
    } else {
        console.log('No votes found in blockchain.');
    }

    console.log();
    console.log('='.repeat(70));
    console.log('ELECTION RESULTS');
    console.log('='.repeat(70));
    console.log();

    // Get results
    const results = queryBlockchain('getResults');
    
    if (results) {
        console.log('Vote Count by Candidate:\n');
        
        // Sort by votes (descending)
        const sorted = Object.entries(results).sort((a, b) => b[1] - a[1]);
        
        sorted.forEach(([candidate, count], index) => {
            const bar = '█'.repeat(count * 5);
            console.log(${index + 1}. ${candidate.padEnd(20)} : ${count} votes ${bar});
        });
        
        const totalVotes = Object.values(results).reduce((sum, count) => sum + count, 0);
        console.log('\n' + '-'.repeat(70));
        console.log(Total Votes Counted: ${totalVotes});
    } else {
        console.log('No results available.');
    }

    console.log();
    console.log('='.repeat(70));
}

function querySpecificVoter(voterId) {
    console.log(\n🔍 Checking if voter "${voterId}" has voted...\n);
    
    const result = queryBlockchain('queryVote', [voterId]);
    
    if (result) {
        if (result.hasVoted) {
            console.log(✅ Voter "${voterId}" HAS voted);
            console.log(`   Transaction ID: ${result.txId}`);
        } else {
            console.log(❌ Voter "${voterId}" has NOT voted);
        }
    }
    console.log();
}

// Main execution
const command = process.argv[2];
const argument = process.argv[3];

switch (command) {
    case 'queryVotes':
    case 'all':
        displayVotes();
        break;
    
    case 'results':
        console.log('='.repeat(70));
        console.log('ELECTION RESULTS ONLY');
        console.log('='.repeat(70));
        const results = queryBlockchain('getResults');
        console.log(JSON.stringify(results, null, 2));
        break;
    
    case 'voter':
        if (!argument) {
            console.log('Usage: node query_blockchain.js voter <voter_id>');
        } else {
            querySpecificVoter(argument);
        }
        break;
    
    default:
        console.log('Usage:');
        console.log('  node query_blockchain.js queryVotes    - Show all votes and results');
        console.log('  node query_blockchain.js results       - Show results only');
        console.log('  node query_blockchain.js voter <id>    - Check if specific voter voted');
        console.log('\nExamples:');
        console.log('  node query_blockchain.js queryVotes');
        console.log('  node query_blockchain.js voter alice123');
}
