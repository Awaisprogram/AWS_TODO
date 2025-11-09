const API_BASE = "/api/todos/";
const todoList = document.getElementById("todoList");
const addBtn = document.getElementById("addBtn");
const todoInput = document.getElementById("todoInput");

async function loadTodos() {
  try {
    const res = await fetch(API_BASE);
    const todos = await res.json();
    renderTodos(todos);
  } catch (err) {
    console.error("Failed to load todos:", err);
  }
}

function renderTodos(todos) {
  todoList.innerHTML = "";
  todos.forEach(todo => {
    const li = document.createElement("li");

    const left = document.createElement("div");
    left.style.display = "flex";
    left.style.alignItems = "center";
    left.style.gap = "8px";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = todo.completed;
    checkbox.className = "checkbox";
    checkbox.addEventListener("change", () => toggleComplete(todo));

    const title = document.createElement("span");
    title.textContent = todo.title;
    title.className = "todo-title" + (todo.completed ? " done" : "");

    left.appendChild(checkbox);
    left.appendChild(title);

    const right = document.createElement("div");

    const editBtn = document.createElement("button");
    editBtn.textContent = "Edit";
    editBtn.className = "small edit";
    editBtn.addEventListener("click", () => editTodoPrompt(todo));

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "Delete";
    deleteBtn.className = "small delete";
    deleteBtn.addEventListener("click", () => deleteTodo(todo.id));

    right.appendChild(editBtn);
    right.appendChild(deleteBtn);

    li.appendChild(left);
    li.appendChild(right);
    todoList.appendChild(li);
  });
}

addBtn.addEventListener("click", async () => {
  const title = todoInput.value.trim();
  if (!title) return alert("Please enter a todo.");
  try {
    await fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, completed: false })
    });
    todoInput.value = "";
    loadTodos();
  } catch (err) {
    console.error("Add failed:", err);
  }
});

async function deleteTodo(id) {
  if (!confirm("Delete this todo?")) return;
  await fetch(API_BASE + id, { method: "DELETE" });
  loadTodos();
}

async function toggleComplete(todo) {
  const updated = { title: todo.title, completed: !todo.completed };
  await fetch(API_BASE + todo.id, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updated)
  });
  loadTodos();
}

function editTodoPrompt(todo) {
  const newTitle = prompt("Edit todo title:", todo.title);
  if (newTitle === null) return; // cancel
  const updated = { title: newTitle.trim() || todo.title, completed: todo.completed };
  fetch(API_BASE + todo.id, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updated)
  }).then(() => loadTodos());
}

loadTodos();
