let timerInterval = null;
let timerTimeout = null;
const LIMIT_TIME = 7; // 10초 제한

function startTimer() {
    stopTimer(); // 기존 작동하던 타이머가 있다면 초기화
    
    const timerUI = document.getElementById('timer-ui');
    const timerBar = document.getElementById('timer-bar');
    timerUI.classList.remove('hidden');
    
    let timeLeft = LIMIT_TIME;
    timerBar.style.width = '100%';
    
    // 0.1초마다 게이지 깎기
    timerInterval = setInterval(() => {
        timeLeft -= 0.1;
        const percentage = (timeLeft / LIMIT_TIME) * 100;
        timerBar.style.width = `${percentage}%`;
        
        if (timeLeft <= 0) {
            stopTimer();
        }
    }, 100);
    
    // 10초 뒤 타임아웃 실행 -> 오답 판정 처리
    timerTimeout = setTimeout(() => {
        handleTimeOver();
    }, LIMIT_TIME * 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
    clearTimeout(timerTimeout);
    document.getElementById('timer-ui').classList.add('hidden');
}

// 시간 초과 시 서버에 임의의 오답(-1)을 전송하여 강제 게임오버 처리
function handleTimeOver() {
    stopTimer();
    
    fetch('/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: 0 }) // 시간 초과 시 오답 처리
    })
    .then(response => response.json())
    .then(data => {
        processNextTurn(data);
    });
}
function processNextTurn(data) {
    const formElement = document.getElementById('game-form');
    const resultElement = document.getElementById('result-message');
    const subGuide = document.getElementById('sub-guide');
    const inputField = document.getElementById('user-input');
    const restartBtn = document.getElementById('restart-btn');
    const homeBtn = document.getElementById('home-btn');

    const currentTurn = data.turn_index || 1;

    if (data.status === 'fail') {
        resultElement.style.fontSize = '1.5rem';
        stopTimer();
        let comparisonHTML = "";
        if (data.correct_answer !== undefined) {
            comparisonHTML = `
                <div style="display: flex; justify-content: center; gap: 20px; margin: 20px 0;">
                    <div>
                        <div style="font-size: 0.9rem; color: #dc2626; margin-bottom: 5px;">내가 쓴 오답 ❌</div>
                        <div class="card-wrong">${data.user_input}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.9rem; color: #16a34a; margin-bottom: 5px;">올바른 정답 ⭕</div>
                        <div class="card-correct">${data.correct_answer}</div>
                    </div>
                </div>
            `;
        }

        resultElement.innerHTML = `
            <div style="font-size: 2rem; color: #dc3545; font-weight: bold; margin-bottom: 10px;">GAME OVER</div>
            <div style="font-size: 1.2rem; font-weight: bold; color: #1e293b; margin-bottom: 15px;">
                최종 기록: <span style="color: #2563eb; font-size: 1.5rem;">${data.score || 0}</span>개 성공! 🎉
            </div>
            ${comparisonHTML}
        `;

        formElement.classList.add('hidden');
        subGuide.classList.add('hidden');
        restartBtn.classList.remove('hidden');
        homeBtn.classList.remove('hidden');

        if (data.history) {
            const historyContainer = document.createElement('div');
            historyContainer.style.marginTop = '20px';
            historyContainer.innerHTML = '<div style="margin-bottom:10px; color:#666; font-size: 0.9rem;">이전 라운드 기록:</div>';
            
            const listWrapper = document.createElement('div');
            listWrapper.style.display = 'flex';
            listWrapper.style.justifyContent = 'center';
            listWrapper.style.gap = '8px';
            listWrapper.style.flexWrap = 'wrap';

            data.history.forEach((num) => {
                const box = document.createElement('div');
                box.innerText = num;
                box.style.padding = '8px 12px';
                box.style.backgroundColor = '#e2e8f0';
                box.style.borderRadius = '6px';
                box.style.fontWeight = 'bold';
                listWrapper.appendChild(box);
            });
            
            historyContainer.appendChild(listWrapper);
            resultElement.appendChild(historyContainer);
        }
        return;
    }

    if (data.next_action === 'user_input') {
        resultElement.style.fontSize = '1.5rem';
        resultElement.innerHTML = `<div style="font-weight: bold; color: #1e293b;">${currentTurn}번째 숫자 입력</div>`;
        startTimer();
        subGuide.classList.remove('hidden');
        formElement.classList.remove('hidden');
        inputField.value = '';
        inputField.focus();
    } 
    else if (data.next_action === 'system_random') {
        formElement.classList.add('hidden');
        subGuide.classList.add('hidden');
        stopTimer();
        resultElement.innerHTML = `
            <div style="font-size: 1.2rem; color: #64748b; margin-bottom: 5px; font-weight: bold;">🎲 ${currentTurn}번째 숫자</div>
            <div class="number-card">${data.random_num}</div>
        `;

        setTimeout(() => {
            fetch('/play', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_input: data.random_num })
            })
            .then(response => response.json())
            .then(nextData => {
                processNextTurn(nextData);
            })
            .catch(error => console.error('Play error:', error));
        }, 2000);
    }
}

function startGame() {
    document.getElementById('start-screen').classList.add('hidden');
    document.getElementById('game-screen').classList.remove('hidden');
    document.getElementById('game-form').classList.add('hidden'); 
    document.getElementById('restart-btn').classList.add('hidden');
    document.getElementById('home-btn').classList.add('hidden');
    document.getElementById('sub-guide').classList.remove('hidden');

    fetch('/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        processNextTurn(data);
    })
    .catch(error => console.error('Start error:', error));
}

function handleSubmit(event) {
    stopTimer();
    event.preventDefault();
    const inputField = document.getElementById('user-input');
    const value = inputField.value;

    fetch('/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: value })
    })
    .then(response => response.json())
    .then(data => {
        processNextTurn(data);
    })
    .catch(error => console.error('Submit error:', error));
}

// [추가] 랭킹 모달 열기
function openRankingModal() {
    document.getElementById('ranking-modal').classList.remove('hidden');
    loadRanking(); // 열릴 때 실시간 데이터 로드
}

// [추가] 랭킹 모달 닫기 (배경을 클릭하거나 닫기 버튼을 누를 때 작동)
function closeRankingModal(event) {
    if (event) {
        event.stopPropagation();
    }
    document.getElementById('ranking-modal').classList.add('hidden');
}

// 랭킹 로드 함수 (기존 스타일 속성 살짝 정리)
function loadRanking() {
    const rankingListDiv = document.getElementById('ranking-list');
    rankingListDiv.innerHTML = '로딩 중...';

    fetch('/ranking')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                if (data.ranking.length === 0) {
                    rankingListDiv.innerHTML = '<div style="text-align:center; color:#94a3b8; padding: 15px 0;">아직 기록이 없습니다. 첫 랭커가 되어보세요!</div>';
                    return;
                }

                let html = '';
                data.ranking.forEach(item => {
                    const rankBadge = `${item.rank}등`;
                    html += `
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px dashed #f1f5f9;">
                            <span style="font-weight: bold; color: #1e293b;">${rankBadge} <span style="margin-left: 8px; color:#2563eb;">${item.score}개</span></span>
                            <span style="font-size: 0.85rem; color: #94a3b8;">${item.date}</span>
                        </div>
                    `;
                });
                rankingListDiv.innerHTML = html;
            } else {
                rankingListDiv.innerHTML = '랭킹을 불러오지 못했습니다.';
            }
        })
        .catch(err => {
            console.error('Ranking load error:', err);
            rankingListDiv.innerHTML = '에러 발생';
        });
}


// 2. 기존 goHome 함수 수정 (홈 화면으로 갈 때 랭킹 갱신)
function goHome() {
    stopTimer();
    document.getElementById('start-screen').classList.remove('hidden');
    document.getElementById('game-screen').classList.add('hidden');
    document.getElementById('game-form').classList.add('hidden');
    document.getElementById('restart-btn').classList.add('hidden');
    document.getElementById('home-btn').classList.add('hidden');
    
    loadRanking(); // 👈 홈으로 갈 때 실시간 기록 반영되도록 갱신 호출
}