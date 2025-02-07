import os
import time
from openai import OpenAI
import streamlit as st

# OpenAI API 설정

openai_api_key = st.secrets["openai_api_key"]
client = OpenAI(api_key=openai_api_key)

# 어시스턴트 생성 함수
def create_assistant(name, instruction, tools=None, model="gpt-4o", temperature=1.0, response_format=None):
    params = {
        "name": name,
        "instructions": instruction,
        "model": model,
        "temperature": temperature,
    }
    if tools:
        params["tools"] = [{"type": tool} for tool in tools]
    if response_format:
        params["response_format"] = response_format

    assistant = client.beta.assistants.create(**params)
    print(f"생성된 어시스턴트 ID: {assistant.id}")
    return assistant.id

# 어시스턴트 삭제 함수
def delete_assistant(assistant_id):
    response = client.beta.assistants.delete(assistant_id)
    print(f"어시스턴트 삭제 응답: {response}")
    return response

# 어시스턴트 업데이트 함수
def update_assistant(assistant_id, name=None, instruction=None, tools=None,vector_store_id =None, model=None, temperature=None, response_format=None):
    params = {}
    if name:
        params["name"] = name
    if instruction:
        params["instructions"] = instruction
    if tools:
        params["tools"] = [{"type": tool} for tool in tools]
    if vector_store_id:
        params["tool_resources"] ={"file_search": {"vector_store_ids": [vector_store_id]}}
    if model:
        params["model"] = model
    if temperature is not None:
        params["temperature"] = temperature
    if response_format:
        params["response_format"] = response_format

    assistant = client.beta.assistants.update(assistant_id, **params)
    print(f"업데이트된 어시스턴트 정보: {assistant}")
    return assistant

# 벡터 스토어 생성 함수
def create_vector_store(name):
    vector_store = client.beta.vector_stores.create(name=name)

    print(f"생성된 벡터 스토어 ID: {vector_store.id}")
    return vector_store.id

# 벡터 스토어 삭제 함수
def delete_vector_store(vector_store_id):
    response = client.beta.vector_stores.delete(vector_store_id)
    print(f"벡터 스토어 삭제 응답: {response}")
    return response

# 벡터 스토어에 파일 추가 함수
def add_files_to_vector_store(vector_store_id, file_paths):
    file_streams = [open(path, "rb") for path in file_paths]

    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store_id,
        files=file_streams
    )

    for file in file_streams:
        file.close()

    print(f"추가된 파일 배치 상태: {file_batch}")
    return file_batch

# 벡터 스토어에서 파일 삭제 함수
def delete_file_from_vector_store(vector_store_id, file_id):
    response = client.beta.vector_stores.files.delete(
        vector_store_id=vector_store_id,
        file_id=file_id
    )
    print(f"벡터 스토어 파일 삭제 응답: {response}")
    return response

# 스트리밍 응답 함수
def response_stream(prompt, thread, assistant, max_retries=5, retry_delay=1):
    retry_count = 0

    # 프롬프트 메시지 추가
    if prompt:
        client.beta.threads.messages.create(
            thread_id=thread,
            role="user",
            content=prompt
        )
        print("프롬프트 전달 완료")

    while retry_count < max_retries:
        try:
            # Streamlit UI를 위한 확장 가능한 컨테이너
            with st.expander(f"어시스턴트: {assistant}의 응답", expanded=True):
                response_container = st.empty()  # 실시간 UI 업데이트를 위한 컨테이너
                full_response = ""  # 응답 누적 변수

                # 스트리밍 실행
                stream = client.beta.threads.runs.create(
                    thread_id=thread,
                    assistant_id=assistant,
                    stream=True  # 스트리밍 활성화
                )

                for event in stream:
                    if event.event == "thread.message.delta":
                        # 텍스트 델타 추출 및 누적
                        for content in event.data.delta.content:
                            if content.type == "text":
                                delta_text = content.text.value
                                full_response += delta_text
                                response_container.markdown(f"```\n{full_response}\n```")  # 실시간 UI 업데이트

                print(f"최종 응답: {full_response}")
                return full_response  # 전체 응답 반환

        except Exception as e:
            retry_count += 1
            st.error(f"실행 실패, 재시도 {retry_count}/{max_retries}... 오류: {e}")
            time.sleep(retry_delay)

    st.error("최대 재시도 횟수 초과. 작업 실패.")
    return None


# 스레드 생성 함수
def create_thread():
    thread = client.beta.threads.create()
    print(f"생성된 스레드 ID: {thread.id}")
    return thread.id

# 스레드 삭제 함수
def delete_thread(thread_id):
    try:
        response = client.beta.threads.delete(thread_id)
        print(f"스레드 삭제 응답: {response}")
        return response
    except Exception as e:
        print(f"스레드 삭제 중 오류 발생: {e}")
        return None
