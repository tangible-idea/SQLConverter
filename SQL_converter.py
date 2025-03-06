import streamlit as st
import json

def read_jsonl(file):
    """JSONL 파일을 읽어 리스트 형태로 변환"""
    return [json.loads(line) for line in file]

def generate_sql_create(table_name, data):
    """ CREATE TABLE SQL 자동 생성 """
    all_keys = set()
    for entry in data:
        all_keys.update(entry.keys())

    columns = []
    for key in sorted(all_keys):
        sample_value = next((entry[key] for entry in data if key in entry), None)
        
        if isinstance(sample_value, bool):  # ✅ 올바르게 BOOLEAN 처리
            col_type = "BOOLEAN"
        elif isinstance(sample_value, int):
            col_type = "INTEGER"
        elif isinstance(sample_value, float):
            col_type = "FLOAT"
        elif isinstance(sample_value, list):
            col_type = "TEXT[]"  # PostgreSQL 배열 타입
        else:
            col_type = "TEXT"
        
        columns.append(f'"{key}" {col_type}')
    
    columns_sql = ",\n    ".join(columns)
    create_sql = "CREATE TABLE {} (\n    {}\n);".format(table_name, columns_sql)

    return create_sql, sorted(all_keys)

def format_value(value):
    """ PostgreSQL에 맞게 데이터를 변환 """
    if isinstance(value, bool):  # ✅ BOOLEAN을 TRUE / FALSE로 변환
        return "TRUE" if value else "FALSE"
    elif isinstance(value, str):
        return "'{}'".format(value.replace("'", "''"))  # SQL 문자열 이스케이프
    elif isinstance(value, list):
        formatted_list = ",".join("'{}'".format(item.replace("'", "''")) for item in value)  # 리스트 요소 처리
        return "ARRAY[{}]".format(formatted_list)  # PostgreSQL ARRAY 형식
    elif value is None:
        return "NULL"
    else:
        return str(value)

def generate_sql_insert(table_name, data, all_keys):
    """ INSERT INTO SQL 자동 생성 (누락된 값은 NULL로 채움) """
    columns = ", ".join('"{}"'.format(key) for key in all_keys)
    values_list = []

    for entry in data:
        values = [format_value(entry.get(key, None)) for key in all_keys]
        values_list.append("({})".format(", ".join(values)))

    values_sql = ",\n    ".join(values_list)
    insert_sql = "INSERT INTO {} ({}) VALUES\n    {};".format(table_name, columns, values_sql)

    return insert_sql

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

        # CREATE TABLE SQL 생성
        create_sql, all_keys = generate_sql_create(table_name, json_data)
        st.subheader("📌 생성된 CREATE TABLE 쿼리")
        st.code(create_sql, language="sql")

        # INSERT INTO SQL 생성 (누락된 값 NULL 처리)
        insert_sql = generate_sql_insert(table_name, json_data, all_keys)
        st.subheader("📌 생성된 INSERT INTO 쿼리")
        st.code(insert_sql, language="sql")

        # SQL 다운로드 파일 생성
        sql_output = "{}\n\n{}".format(create_sql, insert_sql)
        st.download_button("📥 SQL 파일 다운로드", sql_output, file_name="converted.sql", mime="text/sql")

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")