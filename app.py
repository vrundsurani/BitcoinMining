from flask import Flask, jsonify, render_template_string
import sqlite3
import threading
import time
import hashlib
import random

app = Flask(__name__)

# Database setup
DATABASE = "bitcoin_miner.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            balance REAL DEFAULT 0.0,
            blocks_mined INTEGER DEFAULT 0,
            average_time REAL DEFAULT 0.0
        )
    """)
    cursor.execute("INSERT INTO user_data (balance, blocks_mined, average_time) SELECT 0, 0, 0 WHERE NOT EXISTS (SELECT 1 FROM user_data)")
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Global variables for mining state
mining_data = {
    "status": "Idle",
    "difficulty": 5,
    "nonce": 0,
    "hash": "",
    "reward": 6.25,
    "time_taken": 0.0,
    "balance": 0.0,
    "blocks_mined": 0,
    "average_time": 0.0,
}

# Mining Functionality
class BitcoinMiner:
    def __init__(self):
        self.mining = True
        self.paused = False
        self.difficulty = mining_data["difficulty"]
        self.total_time = self.get_user_data()["average_time"]

    def get_user_data(self):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT balance, blocks_mined, average_time FROM user_data LIMIT 1")
        data = cursor.fetchone()
        conn.close()
        return {
            "balance": data[0],
            "blocks_mined": data[1],
            "average_time": data[2],
        }

    def update_user_data(self, balance=None, blocks_mined=None, average_time=None):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        if balance is not None:
            cursor.execute("UPDATE user_data SET balance = ?", (balance,))
        if blocks_mined is not None:
            cursor.execute("UPDATE user_data SET blocks_mined = ?", (blocks_mined,))
        if average_time is not None:
            cursor.execute("UPDATE user_data SET average_time = ?", (average_time,))
        conn.commit()
        conn.close()

    def start_mining(self):
        self.mining = True
        mining_data["status"] = "Mining started..."
        threading.Thread(target=self.mine_block, daemon=True).start()

    def stop_mining(self):
        self.mining = False
        mining_data["status"] = "Mining stopped."

    def pause_mining(self):
        self.paused = not self.paused
        mining_data["status"] = "Mining paused." if self.paused else "Mining resumed."

    def mine_block(self):
        while self.mining:
            if self.paused:
                time.sleep(1)
                continue

            nonce = random.randint(0, 1000000000)
            start_time = time.time()
            while self.mining and not self.paused:
                hash_result = hashlib.sha256(str(nonce).encode()).hexdigest()
                if hash_result.startswith("0" * self.difficulty):
                    end_time = time.time()
                    time_taken = round(end_time - start_time, 2)
                    user_data = self.get_user_data()
                    balance = user_data["balance"] + mining_data["reward"]
                    blocks_mined = user_data["blocks_mined"] + 1
                    average_time = round((self.total_time + time_taken) / blocks_mined, 2)

                    mining_data.update({
                        "status": "Block Mined!",
                        "nonce": nonce,
                        "hash": hash_result,
                        "time_taken": time_taken,
                        "blocks_mined": blocks_mined,
                        "balance": balance,
                        "average_time": average_time,
                    })

                    self.update_user_data(balance=balance, blocks_mined=blocks_mined, average_time=average_time)
                    self.total_time += time_taken
                    self.adjust_reward()
                    self.adjust_difficulty(time_taken)
                    time.sleep(2)
                    break
                nonce += 1
                time.sleep(0.001)
        mining_data["status"] = "Mining stopped."

    def adjust_difficulty(self, time_taken):
        if time_taken < 5:
            self.difficulty += 1
        elif time_taken > 15:
            self.difficulty = max(1, self.difficulty - 1)
        mining_data["difficulty"] = self.difficulty

    def adjust_reward(self):
        if mining_data["blocks_mined"] % 10 == 0:  # Simulate halving every 10 blocks
            mining_data["reward"] = round(mining_data["reward"] / 2, 8)


miner = BitcoinMiner()

# Start automatic mining when the server launches
threading.Thread(target=miner.start_mining, daemon=True).start()

# Flask routes
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitcoin Mining Simulator</title>
    <link rel="icon" href="https://i.postimg.cc/T1HVRN4n/Bit23.png" type="image/png">
    <style>
        body {
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #1a1a1a;
            color: #fff;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            text-align: center;
            padding: 20px;
            background-color: #333;
            border-bottom: 4px solid #f39c12;
        }
        header h1 {
            margin: 0;
            color: #f39c12;
        }
        .actions {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            margin: 20px 0;
        }
        button {
            background-color: #f39c12;
            border: none;
            padding: 10px 20px;
            font-size: 14px;
            border-radius: 5px;
            color: #fff;
            cursor: pointer;
            margin: 5px;
            transition: 0.3s;
        }
        button:hover {
            background-color: #e67e22;
        }
        .status, .results, .balance {
            background-color: #222;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
        }
        .hash-line {
            font-size: calc(2rem + 1vw); /* Responsive font size */
            font-weight: bold;
            overflow-wrap: break-word;
            word-wrap: break-word;
            word-break: break-all;
            line-height: 1.5;
            color: #f39c12;
        }
        @media (max-width: 768px) {
            .hash-line {
                font-size: 1.5rem; /* Smaller font size for smaller screens */
            }
        }
        footer {
            text-align: center;
            margin-top: 20px;
            color: #888;
        }
        @media (max-width: 768px) {
            .actions {
                flex-direction: column;
            }
            button {
                width: 100%;
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>Bitcoin Mining Simulator</h1>
    </header>
    <div class="container">
        <div class="actions">
            <button onclick="stopMining()">Stop Mining</button>
            <button onclick="pauseMining()">Pause/Resume Mining</button>
            <button onclick="increaseDifficulty()">Increase Difficulty</button>
            <button onclick="decreaseDifficulty()">Decrease Difficulty</button>
        </div>
        <div class="status" id="status">Status: Idle</div>
        <div class="balance">
            <p><strong>Bitcoin Balance:</strong> <span id="bitcoin-balance">0.0</span> BTC</p>
            <p><strong>Blocks Mined:</strong> <span id="blocks-mined">0</span></p>
            <p><strong>Average Time:</strong> <span id="average-time">0.0</span> seconds</p>
        </div>
        <div class="results">
            <p class="hash-line"><strong>Nonce:</strong> <span id="nonce">0</span></p>
            <p class="hash-line"><strong>Hash:</strong> <span id="hash">---</span></p>
            <p><strong>Reward:</strong> <span id="reward">0.0</span> BTC</p>
            <p><strong>Time Taken:</strong> <span id="time-taken">0.0</span> seconds</p>
            <p><strong>Difficulty:</strong> <span id="difficulty">0</span></p>
        </div>
    </div>
    <footer>
    <p>© 2024 Bitcoin Mining Simulator</p>
    <p style="font-size: 12px; color: #555;">Made By 
        <a href="https://linktr.ee/BlackJam_" target="_blank" style="font-weight: bold; color: #f39c12; text-decoration: none;">BlackJam TM</a>
    </p>
</footer>
    <script>
        async function updateStatus() {
            const response = await fetch("/status");
            const data = await response.json();
            document.getElementById("status").innerText = `Status: ${data.status}`;
            document.getElementById("bitcoin-balance").innerText = data.balance.toFixed(8);
            document.getElementById("blocks-mined").innerText = data.blocks_mined;
            document.getElementById("average-time").innerText = data.average_time;
            
            const nonceElement = document.getElementById("nonce");
            const hashElement = document.getElementById("hash");
            nonceElement.innerText = data.nonce;
            hashElement.innerText = data.hash;

            // Adjust font size based on hash length
            const length = data.hash.length;
            const fontSize = length > 64 ? "1rem" : "calc(2rem + 1vw)";
            hashElement.style.fontSize = fontSize;

            document.getElementById("reward").innerText = data.reward.toFixed(8);
            document.getElementById("time-taken").innerText = data.time_taken;
            document.getElementById("difficulty").innerText = data.difficulty;
        }

        async function stopMining() { await fetch("/stop", { method: "POST" }); updateStatus(); }
        async function pauseMining() { await fetch("/pause", { method: "POST" }); updateStatus(); }
        async function increaseDifficulty() { await fetch("/difficulty/increase", { method: "POST" }); updateStatus(); }
        async function decreaseDifficulty() { await fetch("/difficulty/decrease", { method: "POST" }); updateStatus(); }

        setInterval(updateStatus, 1000);
    </script>
</body>
</html>
    """)

@app.route("/status")
def get_status():
    return jsonify(mining_data)

@app.route("/stop", methods=["POST"])
def stop():
    miner.stop_mining()
    return jsonify({"message": "Mining stopped!"})

@app.route("/pause", methods=["POST"])
def pause():
    miner.pause_mining()
    return jsonify({"message": "Mining paused/resumed!"})

@app.route("/difficulty/increase", methods=["POST"])
def increase_difficulty():
    miner.difficulty += 1
    mining_data["difficulty"] = miner.difficulty
    return jsonify({"difficulty": miner.difficulty})

@app.route("/difficulty/decrease", methods=["POST"])
def decrease_difficulty():
    if miner.difficulty > 1:
        miner.difficulty -= 1
    mining_data["difficulty"] = miner.difficulty
    return jsonify({"difficulty": miner.difficulty})

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True)
