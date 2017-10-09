# code created following the tutorial at https://hackernoon.com/learn-blockchains-by-building-one-117428612f46

import hashlib
import json
import requests
from time import time
from textwrap import dedent
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.transactions = [];
        self.nodes = set()
        self.newBlock(previousHash=1, proof=100)

    def validateChain(self, chain):
        lastBlock = chain[0]
        currentIndex = 1
        while currentIndex < len(chain):
            block = chain[currentIndex]
            print(json.dumps(lastBlock, indent=4, sort_keys=True))
            print(json.dumps(block, indent=4, sort_keys=True))
            print('\n------------\n')
            if block['previousHash'] != self.hash(lastBlock):
                return False
            if not self.validate(lastBlock['proof'], block['proof']):
                return False
            lastBlock = block
            currentIndex += 1
        return True

    def resolveConflicts(self):
        neighbors = self.nodes
        newChain = None
        maxLength = len(self.chain)
        for node in neighbors:
            res = requests.get('http://{}/chain'.format(node))
            if res.status_code == 200:
                length = res.json()['length']
                chain = res.json()['chain']
                if length > maxLength and self.validateChain(chain):
                    maxLength = length
                    newChain = chain
        if newChain:
            self.chain = newChain
            return True
        return False

    def registerNode(self, address):
        parsedUrl = urlparse(address)
        self.nodes.add(parsedUrl.netloc)

    def newBlock(self, proof, previousHash=None):
        block = {
            'index': len(self.chain) + 1,
            'time': time(),
            'transactions': self.transactions,
            'proof': proof,
            'previousHash': previousHash or self.hash(self.chain[-1])
        }
        self.transactions = []
        self.chain.append(block)
        return block

    def newTransaction(self, sender, recipient, amount):
        self.transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })
        return self.lastBlock['index']+1

    @property
    def lastBlock(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        blockString = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(blockString).hexdigest()

    def prove(self, lastProof):
        proof = 0
        while self.validate(lastProof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def validate(lastProof, proof):
        guessString = '{}{}'.format(lastProof, proof)
        guess = guessString.encode()
        guessHash = hashlib.sha256(guess).hexdigest()
        return guessHash[:4] == '0000'

app = Flask(__name__)
nodeID = str(uuid4()).replace('-', '')
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    lastBlock = blockchain.lastBlock
    lastProof = lastBlock['proof']
    proof = blockchain.prove(lastProof)
    blockchain.newTransaction(
        sender = "0",
        recipient = nodeID,
        amount = 1
    )
    block = blockchain.newBlock(proof)
    res = {
        'message': 'mined block',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previousHash': block['previousHash']
    }
    return jsonify(res), 200

@app.route('/transactions/new', methods=['POST'])
def newTransaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    index = blockchain.newTransaction(
        values['sender'],
        values['recipient'],
        values['amount']
    )
    response = {'message': 'Transaction will be added to Block {}'.format(index)}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def getChain():
    res = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(res), 200

@app.route('/nodes/register', methods=['POST'])
def registerNodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return 'Error: Supply a valid list of nodes', 400

    for node in nodes:
        blockchain.registerNode(node)

    res = {
        'message': 'new nodes added',
        'totalNodes': list(blockchain.nodes)
    }
    return jsonify(res), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolveConflicts()
    if replaced:
        res = {
            'message': 'replaced our chain',
            'newChain': blockchain.chain
        }
    else:
        res = {
            'message': 'our chain is best chain',
            'chain': blockchain.chain
        }
    return jsonify(res), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
