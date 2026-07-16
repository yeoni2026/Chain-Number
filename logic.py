import random

class NumberManager:
    def __init__(self):
        self.num_list = []

    def is_correct(self, user_number):
        try:
            user_number = int(user_number)
        except (ValueError, TypeError):
            return {"status": "fail", "reason": "invalid_input"}

        current_len = len(self.num_list)

        # 1. 이번 칸에 강제수가 있는지 계산
        required_sum = 0
        has_constraint = False
        for prev_index, prev_num in enumerate(self.num_list):
            if prev_index + prev_num == current_len:
                required_sum += prev_num
                has_constraint = True

        if has_constraint and user_number != required_sum:
            return {
                "status": "fail", 
                "reason": "wrong_number", 
                "history": self.num_list,
                "correct_answer": required_sum,
                "user_input": user_number,
                "score": len(self.num_list) # 👈 여태까지 성공적으로 채워진 숫자의 개수 (기록)
            }
        
        # 검증 완료 후 리스트 추가
        self.num_list.append(user_number)

        # 3. '다음 칸'에 강제수가 생기는지 판단
        next_len = len(self.num_list)
        next_has_constraint = False
        for prev_index, prev_num in enumerate(self.num_list):
            if prev_index + prev_num == next_len:
                next_has_constraint = True
                break

        if next_has_constraint:
            return {"status": "success", "next_action": "user_input"}
        else:
            return {"status": "success", "next_action": "system_random"}
        
    def reset(self):
        self.num_list = []