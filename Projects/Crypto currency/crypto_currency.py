import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

class Blockchain:
   def __init__(self):
       self.chain = []
       self.transactions = []
       # create genesis block
       self.create_block(proof = 1, prev_hash='0') # we double quote cause sha256 library only accepted endcoded string
       self.nodes = set()

   def create_block(self, proof, prev_hash):
       block = {
           'index': len(self.chain) + 1,
           'timestamp': str(datetime.datetime.now()),
           'proof': proof,
           'prev_hash': prev_hash,
           'transactions' : self.transactions
       }
       self.transactions = []
       self.chain.append(block)
       return block

   def get_prev_block(self):
       return self.chain[-1]

   def proof_of_work(self, prev_proof):
       new_proof = 1
       check_proof = False
       while check_proof is False:
           hash_operation = hashlib.sha256(str(new_proof**2 - prev_proof**2).encode()).hexdigest()
           if hash_operation[:4] == '0000':
               check_proof = True
           else:
               new_proof += 1

       return new_proof

   def hash(self, block):
       encoded_block = json.dumps(block, sort_keys=True).encode()
       return hashlib.sha256(encoded_block).hexdigest()

   def is_chain_valid(self, chain):
       prev_block =chain[0]
       block_index = 1
       while block_index < len(chain):
           #check the prev_hash property in current block is equal to hash of its previous block
           block = chain[block_index]
           if block['prev_hash'] != self.hash(prev_block):
               return False

           #check proof of all blocks is valid of not
           prev_proof = prev_block['proof']
           proof = block['proof']
           hash_operation = hashlib.sha256(str(proof ** 2 - prev_proof ** 2).encode()).hexdigest()
           if hash_operation[:4] != '0000':
               return False
           prev_block = block
           block_index += 1
       return True

   def add_transaction(self, sender, receiver, amount):
       self.transactions.append({
           'sender' : sender,
           'receiver': receiver,
           'amount': amount
       })
       prev_block = self.get_prev_block()
       return prev_block['index'] + 1

   def add_node(self, address):
       parsed_url = urlparse(address)
       self.nodes.add(parsed_url.netloc)

   def replace_chain(self):
       network = self.nodes
       longest_chain = None
       maxlength = len(self.chain)
       for node in network:
           response = requests.get(f'http://{node}/get_chain')
           if response.status_code == 200:
               length = response.json()['length']
               chain = response.json()['chain']
               if length > maxlength and self.is_chain_valid(chain):
                   maxlength = length
                   longest_chain = chain

       if longest_chain:
           self.chain = longest_chain
           return True
       return False

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
blockchain = Blockchain()
node_address = str(uuid4()).replace('-', '')
@app.route("/mine", methods = ['GET'])
def mine_block():
    prev_block = blockchain.get_prev_block()
    prev_proof = prev_block['proof']
    proof = blockchain.proof_of_work(prev_proof)
    prev_hash = blockchain.hash(prev_block)
    blockchain.add_transaction(sender=node_address, receiver='Tuan', amount=1)

    block = blockchain.create_block(proof, prev_hash)
    response = {'message': "Create successfully",
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'prev_hash': block['prev_hash'],
                'transactions': block['transactions']}
    return jsonify(response)

@app.route('/get_chain', methods = ['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

@app.route('/is_valid', methods = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'mess': "It works"}
    else:
        response = {'mess': "The blockchain is not valid"}

@app.route('/add_transaction', methods = ['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = {'sender', 'receiver', 'amount'}
    if not all (key in json for key in transaction_keys):
        return 'Some keys of a transaction are missing', 400
    index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    response = {'mess': f'This transaction will be added to block {index}'}
    return jsonify(response), 201

# connecting new nodes
@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return "No node", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'mess': 'All nodes are now connected',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201

# replacing the chain by the longest chain if needed
@app.route('/replace_chain', methods = ['GET'])
def replace_chain():
    is_chain_replace = blockchain.replace_chain()
    if is_chain_replace:
        response = {'mess: the chain was replaced by the longest chain'
                    'new_chain': blockchain.chain}
    else:
        response = {"mess": 'all good, the chian is the largest one',
                    'actual_chain': blockchain.chain}

    return jsonify(response), 200

app.run(host='0.0.0.0', port = 5000)