const API = "/api/v1";

const state = {
  token: localStorage.getItem("zechbur_token"),
  user: null,
  stats: null,
  session: null,
  cardIndex: 0,
  answerStartedAt: 0,
  answerLocked: false,
  grammar: null,
  lesson: null,
  exerciseIndex: 0,
  selectedAnswer: null,
  assembled: [],
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
}[char]));

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 2800);
}

async function request(path, options = {}, authenticate = true) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (authenticate && state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 401 && authenticate) {
    localStorage.removeItem("zechbur_token");
    state.token = null;
    await ensureAuth();
    return request(path, options, true);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Ошибка соединения" }));
    throw new Error(body.detail || "Ошибка запроса");
  }
  return response.json();
}

async function ensureAuth() {
  if (state.token) return;
  const telegram = window.Telegram?.WebApp;
  let data;
  if (telegram?.initData) {
    telegram.ready();
    telegram.expand();
    try {
      data = await request("/auth/telegram-webapp", {
        method: "POST",
        body: JSON.stringify({ init_data: telegram.initData }),
      }, false);
    } catch (error) {
      console.warn("Telegram auth failed", error);
    }
  }
  if (!data) {
    data = await request("/auth/guest", {
      method: "POST",
      body: JSON.stringify({ display_name: "Путешественник" }),
    }, false);
  }
  state.token = data.access_token;
  state.user = data.user;
  localStorage.setItem("zechbur_token", state.token);
}

function showView(name) {
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  $$('[data-view]').forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  window.scrollTo({ top: 0, behavior: "smooth" });
  history.replaceState(null, "", `#${name}`);
  if (name === "study") loadStudySession();
  if (name === "grammar") loadGrammar();
  if (name === "dictionary" && !$(".dictionary-item")) searchDictionary("");
}

function updateProfile() {
  if (!state.user) return;
  const firstName = state.user.display_name.split(" ")[0];
  $("#profile-name").textContent = state.user.display_name;
  $("#hello-name").textContent = firstName === "Путешественник" ? "друг" : firstName;
  $("#xp-top").textContent = state.user.xp;
}

async function loadStats() {
  state.stats = await request("/learn/stats");
  const stats = state.stats;
  $("#xp-top").textContent = stats.xp;
  $("#streak-top").textContent = Math.max(stats.streak, 1);
  $("#streak-value").textContent = stats.streak;
  $("#learned-value").textContent = stats.learned;
  $("#accuracy-value").textContent = stats.accuracy_30d;
  $("#goal-count").textContent = stats.reviewed_today;
  $("#goal-total").textContent = stats.daily_goal;
  const ratio = Math.min(stats.reviewed_today / Math.max(stats.daily_goal, 1), 1);
  $("#goal-ring").style.setProperty("--progress", `${ratio * 360}deg`);
  $("#goal-message").textContent = ratio >= 1
    ? "Цель выполнена. Очень красиво!"
    : `Осталось ${Math.max(stats.daily_goal - stats.reviewed_today, 0)} карточек в спокойном темпе.`;
  $("#hero-caption").textContent = stats.due_today
    ? `Вас ждут ${stats.due_today} повторений и несколько новых слов.`
    : "Повторения закончились — самое время познакомиться с новыми словами.";
}

async function loadStudySession(force = false) {
  if (state.session && !force && state.cardIndex < state.session.cards.length) return;
  const card = $("#study-card");
  card.classList.add("loading-card");
  $("#study-word").textContent = "Готовим карточки…";
  $("#answer-options").innerHTML = "";
  $("#answer-reveal").hidden = true;
  try {
    state.session = await request("/learn/session?limit=10");
    state.cardIndex = 0;
    renderStudyCard();
  } catch (error) {
    card.classList.remove("loading-card");
    $("#study-word").textContent = "Не удалось загрузить";
    toast(error.message);
  }
}

function renderStudyCard() {
  const total = state.session?.cards.length || 0;
  if (!total || state.cardIndex >= total) {
    renderSessionComplete();
    return;
  }
  const card = state.session.cards[state.cardIndex];
  state.answerLocked = false;
  state.answerStartedAt = performance.now();
  $("#study-card").classList.remove("loading-card");
  $("#study-word").textContent = card.entry.word;
  $("#word-meta").textContent = [card.entry.part_of_speech, ...card.entry.labels].filter(Boolean).join(" · ");
  $("#session-counter").textContent = `${state.cardIndex + 1} / ${total}`;
  $("#session-progress-bar").style.width = `${(state.cardIndex / total) * 100}%`;
  $("#answer-reveal").hidden = true;
  $("#answer-options").innerHTML = card.options.map((option, index) => `
    <button class="answer-option" data-entry-id="${option.entry_id}">
      <span class="answer-key">${index + 1}</span><span>${esc(option.text)}</span>
    </button>`).join("");
  $$(".answer-option").forEach((button) => button.addEventListener("click", () => revealAnswer(button)));
}

function revealAnswer(button) {
  if (state.answerLocked) return;
  state.answerLocked = true;
  const card = state.session.cards[state.cardIndex];
  const selectedId = Number(button.dataset.entryId);
  const correct = selectedId === card.entry.id;
  $$(".answer-option").forEach((item) => {
    item.disabled = true;
    if (Number(item.dataset.entryId) === card.entry.id) item.classList.add("correct");
  });
  if (!correct) button.classList.add("wrong");
  const reveal = $("#answer-reveal");
  const example = card.entry.examples[0];
  reveal.innerHTML = `
    <span class="eyebrow">${correct ? "Верно · закрепим ощущение" : "Почти · теперь слово станет заметнее"}</span>
    <h3>${esc(card.entry.word)} — ${esc(card.entry.gloss)}</h3>
    <p>${example ? esc(example) : esc(card.entry.definition.slice(0, 420))}</p>
    <div class="reveal-actions"><span>Насколько легко вспомнилось?</span><div class="confidence">
      <button data-confidence="1">Трудно</button><button data-confidence="2">Хорошо</button><button data-confidence="3">Легко</button>
    </div></div>`;
  reveal.hidden = false;
  $$("[data-confidence]", reveal).forEach((confidenceButton) => confidenceButton.addEventListener("click", async () => {
    $$("[data-confidence]", reveal).forEach((item) => { item.disabled = true; });
    await submitReview(correct, Number(confidenceButton.dataset.confidence));
  }));
}

async function submitReview(correct, confidence) {
  const card = state.session.cards[state.cardIndex];
  try {
    const result = await request("/learn/review", {
      method: "POST",
      body: JSON.stringify({
        entry_id: card.entry.id,
        correct,
        confidence,
        response_ms: Math.round(performance.now() - state.answerStartedAt),
      }),
    });
    toast(`+${result.xp_earned} XP · ${result.interval_days ? `следующий показ через ${result.interval_days} дн.` : "повторим через 7 минут"}`);
    state.cardIndex += 1;
    renderStudyCard();
  } catch (error) {
    toast(error.message);
  }
}

function renderSessionComplete() {
  $("#session-progress-bar").style.width = "100%";
  $("#session-counter").textContent = "Готово";
  $("#study-word").textContent = "Ӟечбур!";
  $("#word-meta").textContent = "Сессия завершена";
  $("#answer-options").innerHTML = `<button class="primary-button" id="more-words">Ещё 10 слов →</button><button class="answer-option" data-go-home>Вернуться на главную</button>`;
  $("#answer-reveal").hidden = true;
  $("#more-words").addEventListener("click", () => loadStudySession(true));
  $("[data-go-home]").addEventListener("click", () => showView("home"));
  loadStats();
}

async function loadGrammar(force = false) {
  if (state.grammar && !force) return;
  try {
    state.grammar = await request("/grammar/lessons");
    renderGrammarList();
  } catch (error) {
    toast(error.message);
  }
}

function renderGrammarList() {
  const completed = state.grammar.filter((lesson) => lesson.progress.completed).length;
  $("#grammar-completed").textContent = completed;
  $("#grammar-list").innerHTML = state.grammar.map((lesson) => `
    <button class="lesson-node ${lesson.progress.completed ? "completed" : ""}" data-slug="${lesson.slug}">
      <span class="node-number">${lesson.progress.completed ? "✓" : String(lesson.order).padStart(2, "0")}</span>
      <span><span class="tag">${esc(lesson.stage)}</span><h3>${esc(lesson.title)}</h3><p>${esc(lesson.summary)}</p></span>
      <span class="progress-dot">${lesson.progress.solved}/${lesson.progress.total}</span>
    </button>`).join("");
  $$(".lesson-node").forEach((button) => button.addEventListener("click", () => openLesson(button.dataset.slug)));
}

async function openLesson(slug) {
  state.lesson = await request(`/grammar/lessons/${slug}`);
  state.exerciseIndex = 0;
  state.selectedAnswer = null;
  state.assembled = [];
  $$(".lesson-node").forEach((node) => node.classList.toggle("active", node.dataset.slug === slug));
  renderLesson();
  if (window.innerWidth < 821) $("#lesson-reader").scrollIntoView({ behavior: "smooth" });
}

function renderLesson() {
  const lesson = state.lesson;
  const exercise = lesson.exercises[state.exerciseIndex];
  $("#lesson-reader").innerHTML = `
    <div class="lesson-cover"><span class="eyebrow">${esc(lesson.stage)} · урок ${lesson.order}</span><h2>${esc(lesson.title)}</h2><p>${esc(lesson.summary)}</p></div>
    <div class="lesson-body">
      ${lesson.sections.map((section) => `<section class="theory-block"><h3>${esc(section.title)}</h3><p>${esc(section.body)}</p><div class="examples">${section.examples.map((example) => `<span class="example-chip">${esc(example)}</span>`).join("")}</div></section>`).join("")}
      <section class="exercise-box" id="exercise-box">
        <span class="eyebrow">Практика ${state.exerciseIndex + 1} из ${lesson.exercises.length}</span>
        <h3>${esc(exercise.prompt)}</h3>
        <p>Ответьте, опираясь на правило выше.</p>
        ${exerciseMarkup(exercise)}
        <div id="grammar-feedback"></div>
        <div class="exercise-footer"><span class="source-note">Источник: ${esc(lesson.source)}</span><button class="primary-button" id="check-exercise">Проверить</button></div>
      </section>
    </div>`;
  bindExercise(exercise);
}

function exerciseMarkup(exercise) {
  if (exercise.type === "choice") {
    return `<div class="exercise-options">${exercise.options.map((option) => `<button class="exercise-option" data-answer="${esc(option)}">${esc(option)}</button>`).join("")}</div>`;
  }
  return `<div class="answer-line" id="answer-line"><span class="source-note">Нажмите на части в правильном порядке</span></div><div class="token-bank">${exercise.tokens.map((token, index) => `<button class="token-option" data-token-index="${index}">${esc(token)}</button>`).join("")}</div>`;
}

function bindExercise(exercise) {
  if (exercise.type === "choice") {
    $$(".exercise-option").forEach((button) => button.addEventListener("click", () => {
      state.selectedAnswer = button.dataset.answer;
      $$(".exercise-option").forEach((item) => item.classList.toggle("selected", item === button));
    }));
  } else {
    $$(".token-option").forEach((button) => button.addEventListener("click", () => {
      if (button.classList.contains("used")) return;
      button.classList.add("used");
      state.assembled.push({ index: Number(button.dataset.tokenIndex), value: button.textContent });
      renderAnswerLine();
    }));
  }
  $("#check-exercise").onclick = checkExercise;
}

function renderAnswerLine() {
  const line = $("#answer-line");
  line.innerHTML = state.assembled.map((token, index) => `<button class="token-option" data-remove-token="${index}">${esc(token.value)}</button>`).join("") || `<span class="source-note">Нажмите на части в правильном порядке</span>`;
  $$('[data-remove-token]', line).forEach((button) => button.addEventListener("click", () => {
    const [removed] = state.assembled.splice(Number(button.dataset.removeToken), 1);
    $(`.token-option[data-token-index="${removed.index}"]`).classList.remove("used");
    renderAnswerLine();
  }));
}

async function checkExercise() {
  const exercise = state.lesson.exercises[state.exerciseIndex];
  const answer = exercise.type === "choice" ? state.selectedAnswer : state.assembled.map((item) => item.value);
  if (!answer || (Array.isArray(answer) && !answer.length)) {
    toast("Сначала выберите или соберите ответ");
    return;
  }
  try {
    const result = await request(`/grammar/lessons/${state.lesson.slug}/answer`, {
      method: "POST", body: JSON.stringify({ exercise_id: exercise.id, answer }),
    });
    const feedback = $("#grammar-feedback");
    feedback.className = `feedback ${result.correct ? "good" : "bad"}`;
    feedback.innerHTML = `<strong>${result.correct ? "Точно!" : `Правильный ответ: ${esc(Array.isArray(result.expected) ? result.expected.join(" ") : result.expected)}`}</strong><br>${esc(result.explanation)}`;
    $("#check-exercise").textContent = state.exerciseIndex + 1 < state.lesson.exercises.length ? "Следующее →" : "Завершить →";
    $("#check-exercise").onclick = async () => {
      if (state.exerciseIndex + 1 < state.lesson.exercises.length) {
        state.exerciseIndex += 1; state.selectedAnswer = null; state.assembled = []; renderLesson();
      } else {
        toast(result.completed ? "Урок завершён · открыта новая ступень" : "Урок пройден — вернитесь к сложным вопросам позже");
        await loadGrammar(true);
      }
    };
    if (result.xp_earned) toast(`+${result.xp_earned} XP за грамматику`);
  } catch (error) { toast(error.message); }
}

async function searchDictionary(query) {
  const container = $("#dictionary-results");
  container.innerHTML = `<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>`;
  try {
    const result = await request(`/dictionary/search?q=${encodeURIComponent(query)}&limit=30`);
    $("#results-count").textContent = result.total ? `Найдено: ${result.total.toLocaleString("ru-RU")}` : "Ничего не найдено";
    container.innerHTML = result.items.length ? result.items.map((entry) => `
      <button class="dictionary-item" data-entry="${entry.id}"><strong>${esc(entry.word)}</strong><p>${esc(entry.gloss)}</p><span class="pos-badge">${esc(entry.part_of_speech || entry.labels[0] || "слово")}</span></button>`).join("") : `<div class="empty-state">Попробуйте другую форму или часть перевода.</div>`;
    $$(".dictionary-item").forEach((button) => button.addEventListener("click", () => {
      $$(".dictionary-item").forEach((item) => item.classList.toggle("active", item === button));
      showEntry(Number(button.dataset.entry));
    }));
  } catch (error) { container.innerHTML = `<div class="empty-state">${esc(error.message)}</div>`; }
}

async function showEntry(id) {
  try {
    const entry = await request(`/dictionary/${id}`);
    $("#entry-detail").innerHTML = `<span class="detail-letter">${esc(entry.word[0] || "Ӟ")}</span><h2>${esc(entry.word)}</h2><div class="detail-labels">${[entry.part_of_speech, ...entry.labels].filter(Boolean).map((label) => `<span>${esc(label)}</span>`).join("")}</div><p class="detail-gloss">${esc(entry.gloss)}</p>${entry.examples.slice(0, 3).map((example) => `<div class="detail-example">${esc(example)}</div>`).join("")}<p>${esc(entry.definition.slice(0, 950))}</p>`;
    if (window.innerWidth < 821) $("#entry-detail").scrollIntoView({ behavior: "smooth" });
  } catch (error) { toast(error.message); }
}

function bindNavigation() {
  $$('[data-view]').forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
  $$('[data-go]').forEach((button) => button.addEventListener("click", () => showView(button.dataset.go)));
  $("#search-form").addEventListener("submit", (event) => { event.preventDefault(); searchDictionary($("#search-input").value.trim()); });
  window.addEventListener("keydown", (event) => {
    if (!$("#view-study").classList.contains("active") || state.answerLocked) return;
    const index = Number(event.key) - 1;
    const option = $$(".answer-option")[index];
    if (option) option.click();
  });
}

async function boot() {
  bindNavigation();
  try {
    await ensureAuth();
    if (!state.user) state.user = await request("/auth/me");
    updateProfile();
    await Promise.all([loadStats(), loadGrammar()]);
    const initial = location.hash.slice(1);
    if (["home", "study", "grammar", "dictionary"].includes(initial)) showView(initial);
  } catch (error) {
    toast(`Не удалось запустить приложение: ${error.message}`);
  }
}

boot();
