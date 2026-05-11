from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- 数据库配置 ---
# 将原来的 sqlite:///./todos.db 改为更稳健的写法
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'todos.db')}" # 数据库文件名
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 定义数据库表结构（模型）
class TodoTable(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    is_completed = Column(Boolean, default=False)

# 创建数据库文件
Base.metadata.create_all(bind=engine)

# 获取数据库连接的工具函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FastAPI 逻辑 ---
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许前端访问的设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 这里的 * 表示允许所有地址访问，开发阶段先这么干
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 模型（用于 API 数据验证）
class TodoCreate(BaseModel):
    content: str

@app.get("/", response_class=HTMLResponse)
def get_home():
   return """
    <html>
        <head>
            <title>我的极简待办</title>
            <style>
                body { font-family: sans-serif; max-width: 500px; margin: 50px auto; background: #f4f7f6; }
                .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                input { width: 70%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
                button { padding: 10px; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 4px; }
                ul { list-style: none; padding: 0; margin-top: 20px; }
                li { padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }
                .done { text-decoration: line-through; color: gray; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📝 待办清单</h2>
                <input type="text" id="todoInput" placeholder="输入新任务...">
                <button onclick="addTodo()">添加</button>
                <ul id="todoList"></ul>
            </div>
            <script>
                async function loadTodos() {
                    const res = await fetch('/todos');
                    const data = await res.json();
                    const list = document.getElementById('todoList');
                    list.innerHTML = data.map(t => `
                        <li>
                            <span class="${t.is_completed ? 'done' : ''}">${t.content}</span>
                            <div>
                                <button onclick="toggleTodo(${t.id})" style="background:#007bff; font-size:12px">完成/撤销</button>
                                <button onclick="deleteTodo(${t.id})" style="background:#dc3545; font-size:12px">删除</button>
                            </div>
                        </li>
                    `).join('');
                }

                async function addTodo() {
                    const input = document.getElementById('todoInput');
                    await fetch('/todos', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({id: Date.now(), content: input.value, is_completed: false})
                    });
                    input.value = '';
                    loadTodos();
                }

                async function toggleTodo(id) {
                    await fetch(`/todos/${id}`, { method: 'PUT' });
                    loadTodos();
                }

                async function deleteTodo(id) {
                     if (confirm("确定要删除这条任务吗？")) {
                     await fetch(`/todos/${id}`, { method: 'DELETE' });
                      loadTodos(); // 重新加载列表
                    }
                }
                loadTodos(); // 初始加载
            </script>
        </body>
    </html>
    """
pass 

@app.get("/todos")
def get_todos(db: Session = Depends(get_db)):
    return db.query(TodoTable).all()

@app.post("/todos")
def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    new_todo = TodoTable(content=todo.content)
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    return new_todo

@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, db: Session = Depends(get_db)):
    db_todo = db.query(TodoTable).filter(TodoTable.id == todo_id).first()
    if not db_todo:
        raise HTTPException(status_code=404)
    db_todo.is_completed = not db_todo.is_completed
    db.commit()
    return db_todo

# ... 删除逻辑同理 ...
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    db_todo = db.query(TodoTable).filter(TodoTable.id == todo_id).first()
    if not db_todo:
        raise HTTPException(  status_code=404, detail="任务不存在"    )
    db.delete(db_todo)
    db.commit()
    return {"message": "删除成功", "id": todo_id}