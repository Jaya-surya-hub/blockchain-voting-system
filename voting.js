'use strict';

const { Contract } = require('fabric-contract-api');

class VotingContract extends Contract {

    async initLedger(ctx) {
        console.info('Initialize Ledger');
        
        // Initialize vote counts for Tamil Nadu parties
        const initialCounts = {
            'ADMK': 0,
            'DMK': 0,
            'NTK': 0
        };
        await ctx.stub.putState('VOTE_COUNTS', Buffer.from(JSON.stringify(initialCounts)));
        
        // Initialize validators with stakes (PoS)
        const validators = {
            'peer0.org1.example.com': {
                stake: 1000,
                reputation: 100,
                votes_validated: 0,
                organization: 'Org1MSP'
            },
            'peer0.org2.example.com': {
                stake: 800,
                reputation: 95,
                votes_validated: 0,
                organization: 'Org2MSP'
            }
        };
        await ctx.stub.putState('VALIDATORS', Buffer.from(JSON.stringify(validators)));
        
        console.info('Validators initialized:', validators);
    }

    async submitVote(ctx, voterID, candidate) {
        console.info('Submit Vote');
        const voteKey = VOTE_${voterID};
        const existingVote = await ctx.stub.getState(voteKey);
        
        if (existingVote && existingVote.length > 0) {
            throw new Error(Voter ${voterID} has already voted);
        }

        // Get transaction details
        const txId = ctx.stub.getTxID();
        const mspId = ctx.clientIdentity.getMSPID();
        
        // Record which validator processed this
        const validatorId = peer0.${mspId.toLowerCase().replace('msp', '')}.example.com;

        const vote = {
            voterID: voterID,
            candidate: candidate,
            txId: txId,
            validatedBy: validatorId,
            mspId: mspId,
            docType: 'vote'
        };

        await ctx.stub.putState(voteKey, Buffer.from(JSON.stringify(vote)));

        // Update vote counts
        const countsBuffer = await ctx.stub.getState('VOTE_COUNTS');
        let counts = {};
        
        if (countsBuffer && countsBuffer.length > 0) {
            counts = JSON.parse(countsBuffer.toString());
        } else {
            counts = {
                'ADMK': 0,
                'DMK': 0,
                'NTK': 0
            };
        }

        if (counts[candidate] !== undefined) {
            counts[candidate]++;
        } else {
            counts[candidate] = 1;
        }

        await ctx.stub.putState('VOTE_COUNTS', Buffer.from(JSON.stringify(counts)));
        
        // Update validator stats
        await this._updateValidatorStats(ctx, validatorId);

        return JSON.stringify(vote);
    }

    async _updateValidatorStats(ctx, validatorId) {
        const validatorsBuffer = await ctx.stub.getState('VALIDATORS');
        if (validatorsBuffer && validatorsBuffer.length > 0) {
            const validators = JSON.parse(validatorsBuffer.toString());
            if (validators[validatorId]) {
                validators[validatorId].votes_validated++;
                validators[validatorId].reputation += 0.1; // Increase reputation
                await ctx.stub.putState('VALIDATORS', Buffer.from(JSON.stringify(validators)));
            }
        }
    }

    async getValidators(ctx) {
        console.info('Get Validators');
        const validatorsBuffer = await ctx.stub.getState('VALIDATORS');
        
        if (!validatorsBuffer || validatorsBuffer.length === 0) {
            return JSON.stringify({});
        }

        const validators = JSON.parse(validatorsBuffer.toString());
        return JSON.stringify(validators);
    }

    async updateValidatorStake(ctx, validatorId, newStake) {
        console.info('Update Validator Stake');
        const validatorsBuffer = await ctx.stub.getState('VALIDATORS');
        
        if (!validatorsBuffer || validatorsBuffer.length === 0) {
            throw new Error('Validators not initialized');
        }

        const validators = JSON.parse(validatorsBuffer.toString());
        
        if (!validators[validatorId]) {
            throw new Error(Validator ${validatorId} not found);
        }

        validators[validatorId].stake = parseInt(newStake);
        await ctx.stub.putState('VALIDATORS', Buffer.from(JSON.stringify(validators)));
        
        return JSON.stringify(validators[validatorId]);
    }

    async queryVote(ctx, voterID) {
        const voteKey = VOTE_${voterID};
        const voteBuffer = await ctx.stub.getState(voteKey);

        if (!voteBuffer || voteBuffer.length === 0) {
            return JSON.stringify({ hasVoted: false });
        }

        const vote = JSON.parse(voteBuffer.toString());
        return JSON.stringify({ 
            hasVoted: true, 
            txId: vote.txId,
            validatedBy: vote.validatedBy
        });
    }

    async getResults(ctx) {
        console.info('Get Results');
        const countsBuffer = await ctx.stub.getState('VOTE_COUNTS');
        
        if (!countsBuffer || countsBuffer.length === 0) {
            return JSON.stringify({
                'ADMK': 0,
                'DMK': 0,
                'NTK': 0
            });
        }

        const counts = JSON.parse(countsBuffer.toString());
        return JSON.stringify(counts);
    }

    async getAllVotes(ctx) {
        const allResults = [];
        const iterator = await ctx.stub.getStateByRange('VOTE_', 'VOTE_~');
        
        let result = await iterator.next();
        
        while (!result.done) {
            const strValue = Buffer.from(result.value.value.toString()).toString('utf8');
            let record;
            
            try {
                record = JSON.parse(strValue);
                allResults.push(record);
            } catch (err) {
                console.log(err);
            }
            
            result = await iterator.next();
        }
        
        await iterator.close();
        return JSON.stringify(allResults);
    }
}

module.exports = VotingContract;
