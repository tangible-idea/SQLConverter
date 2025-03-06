import streamlit as st
import json
import pandas as pd
import os  # 파일 이름 처리를 위해 추가

# JSONL 파일 읽기
def read_jsonl(file):
    return [json.loads(line) for line in file]

# 데이터 타입 추론
def infer_column_types(data):
    all_keys = set()
    for entry in data:
        all_keys.update(entry.keys())

    column_types = {}
    for key in sorted(all_keys):
        sample_value = next((entry[key] for entry in data if key in entry), None)
        
        if isinstance(sample_value, bool):
            col_type = "BOOLEAN"
        elif isinstance(sample_value, int):
            col_type = "INTEGER"
        elif isinstance(sample_value, float):
            col_type = "FLOAT"
        elif isinstance(sample_value, list):
            col_type = "TEXT[]"  # PostgreSQL 배열 타입
        else:
            col_type = "TEXT"
        
        column_types[key] = col_type

    return column_types

# CREATE TABLE SQL 생성
def generate_sql_create(table_name, column_types, primary_keys):
    columns_sql = ",\n    ".join(f'"{col}" {dtype}' for col, dtype in column_types.items())

    pk_sql = ""
    if primary_keys:
        pk_columns = ", ".join(f'"{col}"' for col in primary_keys)
        pk_sql = f",\n    PRIMARY KEY ({pk_columns})"

    return f"CREATE TABLE {table_name} (\n    {columns_sql}{pk_sql}\n);"

# INSERT INTO SQL 생성
def format_value(value, dtype):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif isinstance(value, str):
        return "'{}'".format(value.replace("'", "''"))
    elif isinstance(value, list):
        if value:  # 리스트가 비어있지 않은 경우
            formatted_list = ",".join("'{}'".format(str(item).replace("'", "''")) for item in value)
            return f"ARRAY[{formatted_list}]"
        else:  # 빈 배열일 경우
            return f"ARRAY[]::{dtype}"  # 빈 배열에 데이터 타입 명시
    elif value is None:
        return "NULL"
    else:
        return str(value)

def generate_sql_insert(table_name, data, column_types):
    columns = ", ".join(f'"{col}"' for col in column_types.keys())
    values_list = []

    for entry in data:
        values = [format_value(entry.get(col, None), column_types[col]) for col in column_types.keys()]
        values_list.append(f"({', '.join(values)})")

    values_sql = ",\n    ".join(values_list)
    return f"INSERT INTO {table_name} ({columns}) VALUES\n    {values_sql};"

# Streamlit UI
st.title("JSONL → PostgreSQL SQL 변환기")

uploaded_file = st.file_uploader("JSONL 파일 업로드", type=["jsonl"])

if uploaded_file:
    try:
        json_data = read_jsonl(uploaded_file)

        if not json_data:
            st.error("❌ 올바른 JSONL 데이터를 업로드하세요.")
            st.stop()

        # ✅ 파일 이름에서 확장자 제거하여 기본 테이블 이름 설정
        default_table_name = os.path.splitext(uploaded_file.name)[0]

        # ✅ 사용자가 직접 테이블 이름 입력 가능 (기본값: 파일 이름)
        table_name = st.text_input("📌 테이블 이름 입력", value=default_table_name)

        column_types = infer_column_types(json_data)

        # ✅ 테이블 형태로 필드 선택 및 데이터 타입 변경 가능
        st.subheader("📌 변환할 필드 선택, 데이터 타입 수정, PK 지정")

        # 데이터 프레임 생성
        df = pd.DataFrame({
            "사용": [True] * len(column_types),  # 기본적으로 모든 필드 선택됨
            "PK": [False] * len(column_types),   # 기본적으로 PK는 없음
            "필드명": list(column_types.keys()),
            "데이터 타입": list(column_types.values())
        })

        # Streamlit 데이터 편집 기능 제공
        edited_df = st.data_editor(
            df,
            column_config={
                "사용": st.column_config.CheckboxColumn("사용"),
                "PK": st.column_config.CheckboxColumn("PK"),
                "데이터 타입": st.column_config.SelectboxColumn(
                    "데이터 타입", options=["TEXT", "INTEGER", "FLOAT", "BOOLEAN", "TEXT[]"]
                )
            },
            disabled=["필드명"],  # 필드명은 수정 불가능
            use_container_width=True
        )

        # 선택된 필드만 반영
        selected_columns = edited_df[edited_df["사용"]]
        filtered_columns = dict(zip(selected_columns["필드명"], selected_columns["데이터 타입"]))
        primary_keys = list(edited_df[edited_df["PK"]]["필드명"])

        # Run 버튼 표시
        if st.button("🚀 Run (CREATE & INSERT SQL 생성)"):
            if not filtered_columns:
                st.error("❌ 최소한 하나 이상의 필드를 선택해야 합니다.")
                st.stop()

            create_sql = generate_sql_create(table_name, filtered_columns, primary_keys)
            insert_sql = generate_sql_insert(table_name, json_data, filtered_columns)

            st.subheader("📌 생성된 CREATE TABLE 쿼리")
            st.code(create_sql, language="sql")

            st.subheader("📌 생성된 INSERT INTO 쿼리")
            st.code(insert_sql, language="sql")

            # SQL 다운로드 버튼
            sql_output = f"{create_sql}\n\n{insert_sql}"
            st.download_button("📥 SQL 파일 다운로드", sql_output, file_name="converted.sql", mime="text/sql")

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")