import json
import streamlit as st
import time
from datetime import datetime
import os
import tempfile
from assistant_function import create_assistant, delete_assistant, create_thread, delete_thread, response_stream, create_vector_store, add_files_to_vector_store, delete_vector_store, update_assistant


# JSON 파일 로드 함수
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# JSON 파일 저장 함수
def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_all_ids(file_path):
    with open(file_path, "r", encoding='utf-8') as f:
        data = json.load(f)
        return [item["id"] for item in data]
    
def load_all_results(file_path, group_id):
    data = load_json(file_path)
    for item in data:
        if item["id"] == group_id:
            return [result["run_id"] for result in item.get("result", [])]
    return []

def get_result_by_run_id(file_path, group_id, run_id):
    data = load_json(file_path)
    for item in data:
        if item["id"] == group_id:
            for result in item.get("result", []):
                if result["run_id"] == run_id:
                    return result
    return {}

def get_assistants_by_id(file_path, selected_id):
    with open(file_path, "r", encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
            if item["id"] == selected_id:
                return item["assistants"], item
    return [], {}


# 특정 구조에 결과 추가 함수
def add_result_to_group(file_path, group_id, prompt, run_results):
    # JSON 파일 로드
    data = load_json(file_path)
    
    # 해당 그룹 찾기
    for group in data:
        if group["id"] == group_id:
            # 실행 번호(run_id) 설정: 해당 그룹의 result 길이에 +1
            run_id = len(group["results"]) + 1

            # 결과 추가
            group["result"].append({
                "run_id": run_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prompt" : prompt,
                "results": run_results
            })
            break

    # 업데이트된 JSON 저장
    save_json(file_path, data)


def add_new_assistant(file_path, new_item):
    with open(file_path, "r", encoding='utf-8') as f:
        data = json.load(f)
    data.append(new_item)  # 새로운 assistant 추가
    with open(file_path, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def generate_custom_id(name):
    current_time = datetime.now().strftime("%m-%d_%H-%M-%S")
    return f"{name}_{current_time}"

@st.dialog("어시스턴트 편집", width="large")
def edit_assistants(assistants_info):
    st.subheader("기능 구조 편집")

    if not st.session_state.assistants_temp: 
        st.session_state.assistants_temp = assistants_info.copy()

    # 기능 이름
    name_input = st.text_input("새로운 LLM 기능 이름을 입력하세요", st.session_state.id)
    

    def update_assistant_field(index, field, value):
        st.session_state.assistants_temp[index][field] = value

    def update_assistant_field(index, field, value):
        try:
            # 입력된 값을 JSON으로 변환 후 저장
            parsed_value = json.loads(value) if field == "response_format" else value
            st.session_state.assistants_temp[index][field] = parsed_value
        except json.JSONDecodeError:
            st.error("잘못된 JSON 형식입니다. 다시 입력해주세요.")

    # 각 어시스턴트에 대해 UI 생성
    for index, assistant in enumerate(st.session_state.assistants_temp):
        with st.expander(f"노드 {index + 1}", expanded=True):
            # 각 필드별 입력 UI (즉시 세션 반영)
            st.text_input(
                f"어시스턴트 {index + 1} 이름",
                assistant["name"],
                key=f"name_{index}",
                on_change=lambda i=index: update_assistant_field(i, "name", st.session_state[f"name_{i}"])
            )
            st.text_area(
                f"어시스턴트 {index + 1} 지침",
                assistant["instruction"],
                key=f"instruction_{index}",
                on_change=lambda i=index: update_assistant_field(i, "instruction", st.session_state[f"instruction_{i}"])
            )
            st.selectbox(
                f"어시스턴트 {index + 1} 모델",
                ["gpt-4o", "gpt-3.5-turbo"],
                index=["gpt-4o", "gpt-3.5-turbo"].index(assistant["model"]),
                key=f"model_{index}",
                on_change=lambda i=index: update_assistant_field(i, "model", st.session_state[f"model_{i}"])
            )
            st.slider(
                f"어시스턴트 {index + 1} 온도 (Temperature)",
                0.0, 2.0, assistant["temperature"], 0.1,
                key=f"temperature_{index}",
                on_change=lambda i=index: update_assistant_field(i, "temperature", st.session_state[f"temperature_{i}"])
            )
            st.text_area(
                f"어시스턴트 {index + 1} 도구 (comma-separated)",
                ", ".join(assistant["tools"]),
                key=f"tools_{index}",
                on_change=lambda i=index: update_assistant_field(i, "tools", st.session_state[f"tools_{i}"].split(","))
            )

        
            st.text_area(
                f"어시스턴트 {index + 1} 응답 포맷 (JSON, 텍스트 등)",
                json.dumps(assistant.get("response_format", ""), indent=2, ensure_ascii=False) if assistant.get("response_format") else "",
                key=f"response_format_{index}",
                height=100,
                on_change=lambda i=index: update_assistant_field(i, "response_format", st.session_state[f"response_format_{i}"])
            )

            if st.button(f"어시스턴트 삭제", key=f"delete_{index}"):
                del st.session_state.assistants_temp[index]
                st.rerun()
                
                
            

    # 새 어시스턴트 추가 버튼 (추가 후 상태 업데이트)
    if st.button("새 어시스턴트 추가"):
        st.session_state.assistants_temp.append({
            "name": f"New Assistant {len(st.session_state.assistants_temp) + 1}",
            "instruction": None,
            "model": "gpt-4o",
            "temperature": 1.0,
            "tools": [],
            "response_format": None
        })
        st.rerun()
        
        




def main():

    
    if "prompt" not in st.session_state:
        st.session_state.prompt = None
    
    
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None

    if "final_result" not in st.session_state:
        st.session_state.final_result = None

    st.title("프롬프트 설계")
    st.caption("프롬프트의 지침을 수정하고 새로운 프롬프트를 추가하는 프로토타입")

    col1, col2 = st.columns([1, 1])

    with col1:
        
        st.markdown("### 입력 프롬프트")
        st.header("질문 입력")

        # 질문 6개 디폴트 값
        default_questions = [
            ("어떤 성격의 학문에 더 끌리시나요?", "이론적이고 학문적인 탐구"),
            ("본인이 가장 관심 있는 분야는 무엇인가요?", "인문학 (문학, 철학, 역사 등)"),
            ("학문을 선택할 때 가장 중요하게 고려하는 요인은 무엇인가요?", "취업 가능성"),
            ("당신의 성격에 가장 잘 맞는 전공 유형은 무엇이라고 생각하나요?", "분석적이고 논리적인 전공"),
            ("미래 직업과 연결된 전공을 선택할 때 중요하게 생각하는 것은 무엇인가요?", "안정적인 소득"),
            ("어떤 유형의 학습 방식을 선호하시나요?", "강의를 듣고 이해하는 방식")
        ]
        
        # 질문/답변을 session_state에 저장
        if "answers" not in st.session_state:
            st.session_state.answers = [
                ans for (_, ans) in default_questions
            ]

        # 6개 질문을 표시하고, 사용자가 답 변경 가능
        for i, (q, default_ans) in enumerate(default_questions):
            st.write(f"**질문 {i+1}**: {q}")
            st.session_state.answers[i] = st.text_area(
                f"답변 {i+1}", 
                value=st.session_state.answers[i], 
                key=f"question_{i}", 
               
            )

    run =st.button("전공 추천")

    with col2:
        st.header("추천 결과")
        if st.session_state.final_result:
            if st.button("처음부터"):
                st.session_state.thread_id = None
                st.success("스레드가 삭제되었습니다.")
               
        def execute_recommendation():
            if not st.session_state.prompt: 
                st.session_state.prompt = "다음은 사용자의 전공 추천 관련 정보입니다:\n\n" + "\n".join(
                    [f"질문 {i+1}: {q}\n답변: {st.session_state.answers[i]}" for i, (q, _) in enumerate(default_questions)]
                )

            st.session_state.assistant_ids = ["asst_3BEBtAxgdhEtdraW2BjN3tqO", "asst_wIXKvaxsQcghA79vwIj5slX1"]

            if "thread_id" not in st.session_state or not st.session_state.thread_id:
                st.session_state.thread_id = create_thread()
                st.write(f"쓰레드 생성됨: {st.session_state.thread_id}")

            # 프롬프트를 어시스턴트로 전달하고 결과 수집
            for index, assistant_id in enumerate(st.session_state.assistant_ids):
                if index == 0:
                    result = response_stream(st.session_state.prompt, st.session_state.thread_id, assistant_id)
                else:
                    final_result = response_stream(None, st.session_state.thread_id, assistant_id)

            st.session_state.final_result = json.loads(final_result)

            
        # 초기 실행
        if run:
            st.session_state.final_result = None
            execute_recommendation()

        
        if st.session_state.final_result:
            # JSON 데이터를 파싱
            recommendations = st.session_state.final_result.get("recommendations", {})
            
            # 추천 결과를 보기 좋게 출력
            st.subheader("최종 전공 추천 결과")
            for i, (rec_key, rec_value) in enumerate(recommendations.items(), 1):
                st.markdown(f"### 추천 {i}")
                st.write(f"**전공:** {rec_value['major']}")
                st.write(f"**이유:** {rec_value['reason']}")
                st.write("---")  # 구분선
           
            # 추가 요청 입력 창
            st.subheader("추가 요청")
            user_input = st.text_input("질문이나 요청을 입력하세요", key="user_request")

            # 사용자가 입력한 요청을 프롬프트에 추가하고 자동 실행
            if st.button("추가 요청 보내기"):
                if user_input.strip():
                    st.session_state.prompt += f"\n\n추가 요청: {user_input.strip()}"
                    execute_recommendation()  # 추가 요청 시 자동 실행

    

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    main()




###############


