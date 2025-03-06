import streamlit as st
import json
import pandas as pd

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
def generate_sql_create(table_name, column_types):
    columns_sql = ",\n    ".join(f'"{col}" {dtype}' for col, dtype in column_types.items())
    return f"CREATE TABLE {table_name} (\n    {columns_sql}\n);"

# INSERT INTO SQL 생성
def format_value(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif isinstance(value, str):
        return "'{}'".format(value.replace("'", "''"))
    elif isinstance(value, list):
        formatted_list = ",".join("'{}'".format(item.replace("'", "''")) for item in value)
        return "ARRAY[{}]".format(formatted_list)
    elif value is None:
        return "NULL"
    else:
        return str(value)

def generate_sql_insert(table_name, data, column_types):
    columns = ", ".join(f'"{col}"' for col in column_types.keys())
    values_list = []

    for entry in data:
        values = [format_value(entry.get(col, None)) for col in column_types.keys()]
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

        table_name = "users"
        column_types = infer_column_types(json_data)

        # 📌 필드명 및 데이터 타입 테이블 출력
        st.subheader("📌 데이터 필드 및 타입")
        df = pd.DataFrame(list(column_types.items()), columns=["Column Name", "Data Type"])
        st.dataframe(df, height=300)

        # Run 버튼 표시
        if st.button("🚀 Run (CREATE & INSERT SQL 생성)"):
            create_sql = generate_sql_create(table_name, column_types)
            insert_sql = generate_sql_insert(table_name, json_data, column_types)

            st.subheader("📌 생성된 CREATE TABLE 쿼리")
            st.code(create_sql, language="sql")

            st.subheader("📌 생성된 INSERT INTO 쿼리")
            st.code(insert_sql, language="sql")

            # SQL 다운로드 버튼
            sql_output = f"{create_sql}\n\n{insert_sql}"
            st.download_button("📥 SQL 파일 다운로드", sql_output, file_name="converted.sql", mime="text/sql")

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")