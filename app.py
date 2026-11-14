from flask import Flask, render_template, request, jsonify
import random
import uuid
from logic import NumberManager
import os
import json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

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

class GameSession(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    history = db.Column(db.Text, nullable=False, default='[]')

with app.app_context():
    # db.drop_all()
    db.create_all()  # 👈 다시 깨끗한 새 테이블을 만듭니다.

@app.route('/')
def index():
    return render_template(
        'index.html',
        adsense_client_id=os.environ.get('ADSENSE_CLIENT_ID', '').strip(),
        adsense_slot_id=os.environ.get('ADSENSE_SLOT_ID', '').strip()
    )

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html')

@app.route('/start', methods=['POST'])
def start_game():
    game_id = str(uuid.uuid4())
    game_session = GameSession(id=game_id, history='[]')
    db.session.add(game_session)
    db.session.commit()
    first_rand = random.randint(2, 5)
    return jsonify({
        "status": "success",
        "game_id": game_id,
        "next_action": "system_random",
        "random_num": first_rand,
        "turn_index": 1 # 👈 첫 번째 숫자이므로 1
    })

@app.route('/play', methods=['POST'])
def play():
    data = request.get_json(silent=True) or {}
    game_id = data.get('game_id')
    game_session = db.session.get(GameSession, game_id) if game_id else None
    if game_session is None:
        return jsonify({"status": "fail", "reason": "invalid_game"}), 400

    manager = NumberManager()
    manager.num_list = json.loads(game_session.history)
    user_number = data.get('user_input')
    
    verify = manager.is_correct(user_number)
    
    if verify['status'] == 'fail':
        # 게임 실패 시 DB에 기록 저장
        try:
            score_val = len(manager.num_list)
            history_str = json.dumps(manager.num_list)
            
            new_record = GameHistory(score=score_val, history=history_str)
            db.session.add(new_record)
            db.session.delete(game_session)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("데이터 정리 중 에러 발생:", e)

        return jsonify({
            "status": "fail",
            "game_id": game_id,
            "reason": verify.get("reason"),
            "history": manager.num_list,
            "correct_answer": verify.get("correct_answer"),
            "user_input": user_number,
            "score": len(manager.num_list)
        })
    game_session.history = json.dumps(manager.num_list)
    db.session.commit()

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
        "game_id": game_id,
        "next_action": verify['next_action'],
        "random_num": next_rand,
        "turn_index": len(manager.num_list) + 1 # 👈 다음 채워야 할 칸의 번호 (n번째)
    })

# app.py에 추가

@app.route('/ranking', methods=['GET'])
def get_ranking():
    try:
        # 같은 점수의 기록을 묶어 총 게임 수와 상위 비율을 계산
        score_groups = db.session.query(
            GameHistory.score,
            func.count(GameHistory.id).label('achievement_count')
        ).group_by(GameHistory.score) \
         .order_by(GameHistory.score.desc()).all()
        
        total_games = sum(group.achievement_count for group in score_groups)
        ranking_list = []
        games_at_or_above = 0
        for group in score_groups:
            games_at_or_above += group.achievement_count
            exact_top_percent = games_at_or_above * 100 / total_games
            if exact_top_percent < 10:
                top_percent = max(0.1, round(exact_top_percent, 1))
            else:
                top_percent = (games_at_or_above * 100 + total_games - 1) // total_games
            ranking_list.append({
                "score": group.score,
                "achievement_count": group.achievement_count,
                "top_percent": top_percent
            })
        return jsonify({
            "status": "success",
            "total_games": total_games,
            "ranking": ranking_list
        })
    except Exception as e:
        print("랭킹 로드 실패:", e)
        return jsonify({"status": "fail", "message": "랭킹을 불러올 수 없습니다."})

if __name__ == '__main__':
    app.run(debug=True)
