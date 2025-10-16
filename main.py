import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# 数据库连接与表初始化
conn = sqlite3.connect('personal_management.db')
conn.execute("PRAGMA foreign_keys = ON")

conn.execute("""
CREATE TABLE IF NOT EXISTS user_basic (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    gender TEXT CHECK(gender IN ('M', 'F')),
    birth_date DATE,
    email TEXT,
    phone TEXT,
    address TEXT,
    register_time DATETIME DEFAULT CURRENT_TIMESTAMP
);""")

conn.execute("""
CREATE TABLE IF NOT EXISTS personal_schedule (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    location TEXT,
    description TEXT,
    status TEXT CHECK(status IN ('pending', 'in_progress', 'completed', 'cancelled')) DEFAULT 'pending',
    priority TEXT CHECK(priority IN ('not important', 'not so important', 'a little important', 'important', 'very important')),
    category TEXT CHECK(category IN ('work', 'study', 'life', 'health', 'social', 'other')),
    FOREIGN KEY (user_id) REFERENCES user_basic(user_id) ON DELETE CASCADE
);""")

# 设置当前用户ID
current_user_id = 1

# 页面标题
st.title("📅 个人管理信息系统")

# 导航菜单
menu_options = ["个人信息", "日程管理"]
selected = st.sidebar.selectbox("功能菜单", menu_options)

if selected == "个人信息":
    st.header("个人信息管理")

    # 检查用户是否存在
    user_exists = conn.execute(
        "SELECT 1 FROM user_basic WHERE user_id = ?",
        (current_user_id,)
    ).fetchone()

    # 获取当前用户信息
    user_info = conn.execute(
        "SELECT * FROM user_basic WHERE user_id = ?",
        (current_user_id,)
    ).fetchone()

    with st.form("user_form", clear_on_submit=True):
        st.subheader("基本信息")
        name = st.text_input("姓名*", value=user_info[1] if user_info else "")
        gender = st.selectbox("性别", ["M", "F"],
                              index=["M", "F"].index(user_info[2])
                              if user_info and user_info[2] else 0)

        birth_date = st.date_input(
            "出生日期",
            value=datetime.strptime(user_info[3], "%Y-%m-%d").date()
            if user_info and user_info[3] else datetime.now().date(),
            min_value=datetime(1900, 1, 1).date(),
            max_value=datetime.now().date()
        )

        st.subheader("联系方式")
        email = st.text_input("电子邮箱", value=user_info[4] if user_info else "")
        phone = st.text_input("手机号码", value=user_info[5] if user_info else "")
        address = st.text_input("地址", value=user_info[6] if user_info else "")

        submitted = st.form_submit_button("保存信息")
        if submitted:
            if not name:
                st.error("请填写姓名！")
            else:
                try:
                    if user_exists:
                        sql = """
                        UPDATE user_basic SET
                            name = ?, gender = ?, birth_date = ?,
                           email = ?, phone = ?, address = ?
                        WHERE user_id = ?
                        """
                        conn.execute(sql, (
                            name, gender, birth_date.strftime("%Y-%m-%d"),
                            email, phone, address, current_user_id
                        ))
                    else:
                        sql = """
                        INSERT INTO user_basic 
                        (user_id, name, gender, birth_date, email, phone, address)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """
                        conn.execute(sql, (
                            current_user_id, name, gender, birth_date.strftime("%Y-%m-%d"),
                            email, phone, address
                        ))
                    conn.commit()
                    st.success("个人信息保存成功！")
                except Exception as e:
                    st.error(f"保存失败: {e}")

    # 显示用户信息
    if user_info:
        st.subheader("当前个人信息")
        user_df = pd.read_sql(
            "SELECT name, gender, birth_date, email, phone, address FROM user_basic WHERE user_id = ?",
            conn,
            params=(current_user_id,)
        )
        st.dataframe(user_df)

elif selected == "日程管理":
    st.header("日程管理")

    # 功能选项
    func_option = st.selectbox("操作类型", ["查看日程", "添加日程", "修改日程", "删除日程"])

    if func_option == "查看日程":
        st.subheader("我的日程")

        view_options = ["所有日程", "待办日程", "进行中", "已完成", "按分类查看", "按优先级查看"]
        view_choice = st.selectbox("查看方式", view_options, key="view_choice_selectbox")

        base_sql = """
        SELECT event_id, title, datetime(start_time) as start_time, 
               datetime(end_time) as end_time, location, description,
               status, priority, category 
        FROM personal_schedule 
        WHERE user_id = ? 
        """

        # 初始化查询参数
        sql = base_sql
        params = [current_user_id]

        if view_choice == "所有日程":
            sql = base_sql + " ORDER BY start_time ASC"
            params = (current_user_id,)
        elif view_choice == "待办日程":
            sql = base_sql + " AND status = 'pending' ORDER BY start_time ASC"
            params = (current_user_id,)
        elif view_choice == "进行中":
            sql = base_sql + " AND status = 'in_progress' ORDER BY start_time ASC"
            params = (current_user_id,)
        elif view_choice == "已完成":
            sql = base_sql + " AND status = 'completed' ORDER BY start_time DESC"
            params = (current_user_id,)
        elif view_choice == "按分类查看":
            category = st.selectbox("选择分类", ["work", "study", "life", "health", "social", "other"], key="category_selectbox")
            sql += "AND category = ? ORDER BY start_time ASC"
            params.append(category)
        elif view_choice == "按优先级查看":
            priority = st.selectbox("选择优先级", ["not important", "not so important", "a little important", "important", "very important"])
            sql += "AND priority = ? ORDER BY start_time ASC"
            params.append(priority)

        df = pd.read_sql(sql, conn, params=tuple(params))
        st.dataframe(df)

    elif func_option == "添加日程":
        st.subheader("添加新日程")
        with st.form("add_schedule_form", clear_on_submit=True):
            title = st.text_input("标题*")
            col1, col2 = st.columns(2)
            start_date = col1.date_input("开始日期*")
            start_time = col2.time_input("开始时间*")
            end_date = col1.date_input("结束日期")
            end_time = col2.time_input("结束时间")
            location = st.text_input("地点")
            description = st.text_area("描述")
            status = st.selectbox("状态", ["pending", "in_progress", "completed", "cancelled"])
            priority = st.selectbox("优先级", ["not important", "not so important", "a little important", "important", "very important"], key="priority_selectbox")
            category = st.selectbox("分类", ["work", "study", "life", "health", "social", "other"])

            submitted = st.form_submit_button("添加日程")
            if submitted:
                if not title:
                    st.error("请填写标题！")
                else:
                    start_datetime = f"{start_date.strftime('%Y-%m-%d')} {start_time.strftime('%H:%M:%S')}"
                    end_datetime = f"{end_date.strftime('%Y-%m-%d')} {end_time.strftime('%H:%M:%S')}" if end_date and end_time else None
                    sql = """
                    INSERT INTO personal_schedule 
                    (user_id, title, start_time, end_time, location, 
                     description, status, priority, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    conn.execute(sql, (
                        current_user_id, title, start_datetime, end_datetime,
                        location, description, status, priority, category
                    ))
                    conn.commit()
                    st.success("日程添加成功！")

    elif func_option == "修改日程":
        st.subheader("修改日程")

        events = conn.execute(
            "SELECT event_id, title FROM personal_schedule WHERE user_id = ? ORDER BY start_time",
            (current_user_id,)
        ).fetchall()

        if not events:
            st.info("没有可修改的日程")
        else:
            selected_event = st.selectbox("选择要修改的日程", [f"{eid}: {title}" for eid, title in events])
            event_id = selected_event.split(":")[0].strip()

            event_details = conn.execute(
                "SELECT * FROM personal_schedule WHERE event_id = ?",
                (event_id,)
            ).fetchone()

            if event_details:
                with st.form("update_schedule_form"):
                    title = st.text_input("标题*", value=event_details[2])
                    col1, col2 = st.columns(2)
                    start_datetime = datetime.strptime(event_details[3], "%Y-%m-%d %H:%M:%S")
                    start_date = col1.date_input("开始日期*", value=start_datetime.date())
                    start_time = col2.time_input("开始时间*", value=start_datetime.time())

                    if event_details[4]:
                        end_datetime = datetime.strptime(event_details[4], "%Y-%m-%d %H:%M:%S")
                        end_date = col1.date_input("结束日期", value=end_datetime.date())
                        end_time = col2.time_input("结束时间", value=end_datetime.time())
                    else:
                        end_date = col1.date_input("结束日期")
                        end_time = col2.time_input("结束时间")

                    location = st.text_input("地点", value=event_details[5] or "")
                    description = st.text_area("描述", value=event_details[6] or "")
                    status = st.selectbox("状态", ["pending", "in_progress", "completed", "cancelled"],
                                          index=["pending", "in_progress", "completed", "cancelled"].index(event_details[7]))
                    priority = st.selectbox(
                        "优先级",
                        ["not important", "not so important", "a little important", "important", "very important"],
                        index=["not important", "not so important", "a little important", "important", "very important"].index(event_details[8])
                    )
                    category = st.selectbox("分类", ["work", "study", "life", "health", "social", "other"],
                                            index=["work", "study", "life", "health", "social", "other"].index(event_details[9]))

                    submitted = st.form_submit_button("更新日程")
                    if submitted:
                        if not title:
                            st.error("请填写标题！")
                        else:
                            new_start = f"{start_date} {start_time.strftime('%H:%M:%S')}"
                            new_end = f"{end_date} {end_time.strftime('%H:%M:%S')}" if end_date else None

                            sql = """
                            UPDATE personal_schedule SET
                                title = ?, start_time = ?, end_time = ?, 
                                location = ?, description = ?, status = ?,
                                priority = ?, category = ?
                            WHERE event_id = ?
                            """
                            conn.execute(sql, (
                                title, new_start, new_end,
                                location, description, status,
                                priority, category, event_id
                            ))
                            conn.commit()
                            st.success("日程更新成功！")

    elif func_option == "删除日程":
        st.subheader("删除日程")

        events = conn.execute(
            "SELECT event_id, title FROM personal_schedule WHERE user_id = ? ORDER BY start_time",
            (current_user_id,)
        ).fetchall()

        if not events:
            st.info("没有可删除的日程")
        else:
            selected_event = st.selectbox("选择要删除的日程", [f"{eid}: {title}" for eid, title in events])
            event_id = selected_event.split(":")[0].strip()

            if st.button("确认删除"):
                conn.execute(
                    "DELETE FROM personal_schedule WHERE event_id = ?",
                    (event_id,)
                )
                conn.commit()
                st.success("日程删除成功！")

# 关闭数据库连接
conn.close()
