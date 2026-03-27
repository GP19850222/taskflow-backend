import duckdb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from fastapi import HTTPException # Import thêm để xử lý lỗi

app = FastAPI()

# 2. Danh sách các "nguồn" (Origins) được phép truy cập vào API này
# Trong quá trình phát triển, Next.js mặc định chạy ở port 3000
origins = ["http://localhost:3000","http://127.0.0.1:3000","https://fastapi-example-hjcz.onrender.com"] # Cho phép tất cả các nguồn truy cập

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Cho phép các nguồn đã định nghĩa ở trên truy cập vào API
    allow_credentials=True, # Cho phép gửi cookie và thông tin xác thực trong yêu cầu
    allow_methods=["*"], # Cho phép tất cả các phương thức HTTP (GET, POST, PUT, DELETE, v.v.)
    allow_headers=["*"], # Cho phép tất cả các header trong yêu cầu
)
con = duckdb.connect("taskflow.db", read_only=False) # Kết nối đến cơ sở dữ liệu DuckDB, nếu file không tồn tại sẽ được tạo mới

con.execute("""
CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        title TEXT,
        description TEXT,
        is_completed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

class Task(BaseModel):
    id: int # ID bắt buộc phải có và là kiểu int
    title: str #Tiều đề của task, bắt buộc phải có và là kiểu string
    description: Optional[str] = None # Mô tả của task, không bắt buộc và là kiểu string
    is_completed: bool = False # Trạng thái hoàn thành của task, bắt buộc phải có và mặc định là False
    created_at: datetime = Field(default_factory=datetime.now) # Thời gian tạo của task, bắt buộc phải có và mặc định là thời gian hiện tại
    updated_at: datetime = Field(default_factory=datetime.now) # Thời gian cập nhật của task, bắt buộc phải có và mặc định là thời gian hiện tại

# task_db =[] # Danh sách tạm để lưu trữ các task

@app.get("/tasks/") # Định nghĩa endpoint để lấy danh sách các task
def get_tasks():
    result = con.execute("SELECT id, title, description, is_completed, created_at, updated_at FROM tasks").fetchall()
    return [{"id":r[0], "title":r[1], "description":r[2], "is_completed":r[3], "created_at":r[4], "updated_at":r[5]} for r in result] # Trả về danh sách các task dưới dạng JSON

@app.get("/tasks/{task_id}") # Định nghĩa endpoint để lấy thông tin của một task cụ thể dựa trên ID
def get_task_by_id(task_id: int):
    """Lấy thông tin của một task cụ thể dựa trên ID"""
    result = con.execute("SELECT id, title, description, is_completed, created_at, updated_at FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if result:
        return {"id": result[0], "title": result[1], "description": result[2], "is_completed": result[3], "created_at": result[4], "updated_at": result[5]}
    raise HTTPException(status_code=404, detail="Task không tồn tại") # Nếu không tìm thấy task nào có ID trùng khớp, trả về lỗi 404 với thông báo "Task không tồn tại"

@app.post("/tasks/") # Định nghĩa endpoint để tạo một task mới
def create_task(task: Task):
    try:
        """Tạo một task mới và thêm vào cơ sở dữ liệu"""
        con.execute(
            "INSERT INTO tasks (id, title, description, is_completed, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (task.id, task.title, task.description, task.is_completed, task.created_at, task.updated_at)
        )
        return {"message": "Task được tạo thành công", "task": task} # Trả về thông báo và thông tin của task mới tạo
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) # Nếu có lỗi xảy ra trong quá trình tạo task, trả về lỗi 400 với thông báo lỗi chi tiết
@app.patch("/tasks/{task_id}")
def toggle_task_status(task_id: int):
    # Định nghĩa endpoint để cập nhật thông tin của một task cụ thể dựa trên ID
    current = con.execute("SELECT is_completed FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="Task không tồn tại") # Nếu không tìm thấy task nào có ID trùng khớp, trả về lỗi 404 với thông báo "Task không tồn tại"
    new_status = not current[0] # Đảo ngược trạng thái hoàn thành hiện tại
    con.execute("UPDATE tasks SET is_completed = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, task_id)) # Cập nhật trạng thái hoàn thành mới và thời gian cập nhật
    return {"message": "Trạng thái task đã được cập nhật", "task_id": task_id, "is_completed": new_status} # Trả về thông báo và thông tin của task đã được cập nhật
    pass
@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    # Định nghĩa endpoint để xóa một task cụ thể dựa trên ID
    current = con.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="Task không tồn tại") # Nếu không tìm thấy task nào có ID trùng khớp, trả về lỗi 404 với thông báo "Task không tồn tại"
    con.execute("DELETE FROM tasks WHERE id = ?", (task_id,)) # Xóa task có ID trùng khớp khỏi cơ sở dữ liệu
    return {"message": "Đã xóa task thành công", "task_id": task_id} # Trả về thông báo và ID của task đã được xóa

print("Server đang chạy...")
print("task_db:", get_tasks()) # In ra danh sách các task hiện có trong cơ sở dữ liệu tạm thời

@app.get("/stats")
def get_stats():
    # Đếm số task theo trạng thái is_completed
    results = con.execute("""
        SELECT 
            CASE WHEN is_completed THEN 'Hoàn thành' ELSE 'Đang làm' END as status,
            COUNT(*) as count
        FROM tasks
        GROUP BY is_completed
    """).fetchall()
    
    # Trả về định dạng: [{"status": "Hoàn thành", "count": 5}, ...]
    return [{"status": r[0], "count": r[1]} for r in results]
