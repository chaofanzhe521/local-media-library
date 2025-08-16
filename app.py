# app.py
from flask import Flask, render_template, request, jsonify
import sqlite3
import webbrowser
import threading
from tkinter import Tk, filedialog
import os
from flask import send_file 
import urllib.parse 
import signal

app = Flask(__name__)
DATABASE = 'media_data.db'

# 创建一个函数，用来初始化数据库和表
def init_database():
    """检查数据库和表是否存在，如果不存在则创建它们。"""
    # 检查数据库文件是否存在，如果不存在，conn 会自动创建它
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 检查 media 表是否存在，不存在则创建
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        filepath TEXT NOT NULL UNIQUE,
        media_type TEXT NOT NULL,
        tags TEXT,
        cover_path TEXT,
        view_count INTEGER DEFAULT 0,
        add_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 检查 tags_config 表是否存在，不存在则创建
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tags_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )''')

    # (可选) 如果想让新用户有一些默认标签，可以加这段逻辑
    cursor.execute("SELECT count(*) FROM tags_config")
    if cursor.fetchone()[0] == 0:
        print("tags_config 表为空，插入默认标签...")
        default_tags = [("美食",), ("旅游",), ("游戏",)]
        cursor.executemany("INSERT INTO tags_config (name) VALUES (?)", default_tags)

    conn.commit()
    conn.close()
    print(f"数据库 '{DATABASE}' 已检查并初始化完毕。")

def get_db_connection():
    """建立数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # 这让我们可以像字典一样访问列
    return conn

# --- 页面路由 ---
@app.route('/')
def index():
    """渲染主浏览页面"""
    return render_template('index.html')

@app.route('/manage')
def manage():
    """渲染管理页面"""
    return render_template('manage.html')

# --- API 路由 ---

@app.route('/api/media', methods=['GET'])
def get_media():
    """获取媒体列表，支持按标题、标签和类型筛选"""
    query_title = request.args.get('title') # 新增：获取标题参数
    query_tags = request.args.get('tags')
    query_type = request.args.get('type')
    
    conn = get_db_connection()
    # 使用参数化查询，防止SQL注入
    query = "SELECT * FROM media WHERE 1=1"
    params = []
    
    if query_title:
        query += " AND title LIKE ?"
        params.append(f"%{query_title}%") # 使用 % 实现模糊搜索

    if query_type:
        query += " AND media_type = ?"
        params.append(query_type)
        
    if query_tags:
        tags_list = query_tags.split(',')
        for tag in tags_list:
            if tag.strip(): # 确保标签不为空
                query += " AND tags LIKE ?"
                params.append(f"%{tag.strip()}%")
            
    query += " ORDER BY add_date DESC"
    
    items = conn.execute(query, tuple(params)).fetchall() # 将列表转为元组
    conn.close()
    return jsonify([dict(ix) for ix in items])


@app.route('/api/media', methods=['POST'])
def add_media():
    """从前端接收数据，添加新的媒体条目"""
    new_media = request.get_json()
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO media (title, filepath, media_type, tags, cover_path) VALUES (?, ?, ?, ?, ?)',
            (new_media['title'], new_media['filepath'], new_media['media_type'], new_media['tags'], new_media.get('cover_path'))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'status': 'error', 'message': '文件路径已存在'}), 400
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/media/<int:media_id>', methods=['DELETE'])
def delete_media(media_id):
    """删除一个媒体条目"""
    conn = get_db_connection()
    conn.execute('DELETE FROM media WHERE id = ?', (media_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})
    
@app.route('/api/view/<int:media_id>', methods=['POST'])
def record_view(media_id):
    """记录一次观看"""
    conn = get_db_connection()
    conn.execute('UPDATE media SET view_count = view_count + 1 WHERE id = ?', (media_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/select-file', methods=['GET'])
def select_file():
    """
    弹出文件选择框。
    新增功能：可以接收一个 `filename` 参数，用于预设对话框。
    """
    # 从请求参数中获取文件名，如果没有则为空字符串
    initial_filename = request.args.get('filename', '')
    file_type = request.args.get('type', 'all')
    
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    if file_type == 'image':
        filetypes = [("Image files", "*.jpg *.jpeg *.png *.gif"), ("All files", "*.*")]
    else:
        filetypes = [("All files", "*.*")]
        
    # 【核心修改】在这里使用 initialfile 参数
    filepath = filedialog.askopenfilename(
        parent=root,
        filetypes=filetypes,
        title=f"请选择文件（刚才拖拽的是 {initial_filename} 吗？）", # 友好的标题提示
        initialfile=initial_filename # 设置初始文件名
    )
    root.destroy()
    return jsonify({'filepath': filepath})

# 新增一个路由来提供媒体文件服务
@app.route('/files/<path:encoded_filepath>')
def serve_file(encoded_filepath):
    """
    一个更健壮的文件服务路由，能正确处理编码后的 Windows 路径。
    """
    try:
        # 1. 解码 URL 编码的路径
        filepath = urllib.parse.unquote(encoded_filepath)
        print(f"URL Decoded Path: {filepath}")

        # 2. 检查文件是否存在
        if not os.path.exists(filepath):
            print(f"Error: File not found at path: {filepath}")
            return "File not found", 404

        # 3. 使用 send_file 发送文件
        # send_file 可以直接处理绝对路径，比 send_from_directory 更简单
        print(f"Success: Serving file: {filepath}")
        return send_file(filepath)

    except Exception as e:
        print(f"An error occurred: {e}")
        return "Internal server error", 500

# 【修改】/api/tags 路由，让它从数据库读取
@app.route('/api/tags', methods=['GET'])
def get_preset_tags():
    """从数据库返回所有可用的标签"""
    conn = get_db_connection()
    tags_cursor = conn.execute('SELECT name FROM tags_config ORDER BY name').fetchall()
    conn.close()
    # 将结果从 [(tag1,), (tag2,)] 转换为 [tag1, tag2]
    tags = [row['name'] for row in tags_cursor]
    return jsonify(tags)

# 【新增】用于添加新标签的 API
@app.route('/api/tags', methods=['POST'])
def add_tag():
    """添加一个新的标签到数据库"""
    data = request.get_json()
    tag_name = data.get('name', '').strip()

    if not tag_name:
        return jsonify({'status': 'error', 'message': '标签名不能为空'}), 400

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO tags_config (name) VALUES (?)', (tag_name,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'name': tag_name})
    except sqlite3.IntegrityError: # 捕获 UNIQUE 约束失败的错误
        conn.close()
        return jsonify({'status': 'error', 'message': '标签已存在'}), 409 # 409 Conflict

# 【新增】用于删除标签的 API
@app.route('/api/tags/<tag_name>', methods=['DELETE'])
def delete_tag(tag_name):
    """从数据库删除一个标签"""
    conn = get_db_connection()
    # 注意：这里我们不检查标签是否正在被使用，直接删除。
    # 如果需要更复杂的功能（如删除前检查），可以在此添加逻辑。
    conn.execute('DELETE FROM tags_config WHERE name = ?', (tag_name,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# --- 新增页面路由 ---
@app.route('/tags-management')
def tags_management_page():
    """渲染标签管理页面"""
    return render_template('tags.html')

# 【新增】一个用于安全关闭服务器的 API 路由
@app.route('/shutdown', methods=['POST'])
def shutdown():
    """接收关闭请求，并关闭服务器进程。"""
    print("服务器接收到关闭请求，即将退出...")
    # 使用 os.kill 来发送一个信号，以终止当前进程
    # signal.SIGINT 模拟了按下 Ctrl+C 的效果，是一种比较优雅的退出方式
    os.kill(os.getpid(), signal.SIGINT)
    return '服务器正在关闭...'

def open_browser():
    """在新线程中打开浏览器，避免阻塞主程序"""
    webbrowser.open_new("http://127.0.0.1:5000/")

# 推荐的、兼顾开发与发布的版本

if __name__ == '__main__':
    # 1. 初始化数据库（无论何种模式都需要）
    init_database()
    
    # --- 这是唯一的“开关”，用来切换模式 ---
    DEBUG_MODE = False
    # ------------------------------------

    if DEBUG_MODE:
        # 开发模式下的行为
        print("="*50)
        print("程序以【开发模式】启动...")
        print("访问 http://127.0.0.1:5000")
        print("修改代码后服务器会自动重启。")
        print("="*50)
        # 使用 Flask 自带的开发服务器，它支持 debug=True
        app.run(host='127.0.0.1', port=5000, debug=True)
    else:
        # 发布模式下的行为
        print("="*50)
        print("媒体库已启动！")
        print("请在浏览器中访问: http://127.0.0.1:5000")
        print("要关闭程序，请点击网页上的“退出程序”按钮。")
        print("="*50)
        
        # 自动打开浏览器
        import threading
        import webbrowser
        def open_browser():
            webbrowser.open_new("http://127.0.0.1:5000/")
        threading.Timer(1.25, open_browser).start()
        
        # 使用 waitress 生产服务器
        from waitress import serve
        serve(app, host='127.0.0.1', port=5000)

   
