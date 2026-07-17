from flask import Flask, render_template, request, jsonify
import random
from logic import NumberManager
import os
import json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Render.com 배포 시 환경 변수 사용, 로컬에서는 sqlite 파일 사용
database_url = os.environ.get("DATABASE_URL", "sqlite:///game.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# DB 모델 정의
class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    history = db.Column(db.Text, nullable=False)  # "[3, 2, 4...]" 형태로 저장
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 앱 실행 시 자동으로 테이블 생성 (로컬 game.db 파일 자동 생성됨)
with app.app_context():
    db.create_all()

manager = NumberManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_game():
    manager.reset()
    first_rand = random.randint(2, 5)
    return jsonify({
        "status": "success",
        "next_action": "system_random",
        "random_num": first_rand,
        "turn_index": 1 # 👈 첫 번째 숫자이므로 1
    })

@app.route('/play', methods=['POST'])
def play():
    data = request.get_json()
    user_number = data.get('user_input')
    
    verify = manager.is_correct(user_number)
    
    if verify['status'] == 'fail':
        # 게임 실패 시 DB에 기록 저장
        try:
            score_val = len(manager.num_list)
            history_str = json.dumps(manager.num_list)
            
            new_record = GameHistory(score=score_val, history=history_str)
            db.session.add(new_record)
            db.session.commit()
            records_to_delete = GameHistory.query \
                .order_by(GameHistory.score.desc()) \
                .offset(5) \
                .all()
            
            # 3. 6등 이하 데이터가 존재한다면 한 번에 삭제
            if records_to_delete:
                for record in records_to_delete:
                    db.session.delete(record)
                db.session.commit() # 변경사항 반영
                
        except Exception as e:
            db.session.rollback()
            print("데이터 정리 중 에러 발생:", e)

        return jsonify({
            "status": "fail",
            "reason": verify.get("reason"),
            "history": manager.num_list,
            "correct_answer": verify.get("correct_answer"),
            "user_input": user_number,
            "score": len(manager.num_list)
        })
    next_rand = None
    if verify['next_action'] == 'system_random':
        last_num = manager.num_list[-1] if manager.num_list else None
        candidates = [i for i in [2, 3, 4, 5] if i != last_num]

        #순환족보 방지
        if len(manager.num_list) >= 2:
            if manager.num_list[-2] == 4 and manager.num_list[-1] == 2 and 4 in candidates:
                candidates.remove(4)

        next_rand = random.choice(candidates)
        
    return jsonify({
        "status": "success",
        "next_action": verify['next_action'],
        "random_num": next_rand,
        "turn_index": len(manager.num_list) + 1 # 👈 다음 채워야 할 칸의 번호 (n번째)
    })

# app.py에 추가

@app.route('/ranking', methods=['GET'])
def get_ranking():
    try:
        # score 기준 내림차순으로 상위 5개 기록 조회
        top_records = GameHistory.query.order_by(GameHistory.score.desc()).limit(5).all()
        
        ranking_list = []
        for index, record in enumerate(top_records):
            ranking_list.append({
                "rank": index + 1,
                "score": record.score,
                # 날짜를 '07-16 13:42' 같은 읽기 쉬운 포맷으로 변경
                "date": record.created_at.strftime('%m-%d %H:%M') 
            })
        return jsonify({"status": "success", "ranking": ranking_list})
    except Exception as e:
        print("랭킹 로드 실패:", e)
        return jsonify({"status": "fail", "message": "랭킹을 불러올 수 없습니다."})

if __name__ == '__main__':
    app.run(debug=True)
