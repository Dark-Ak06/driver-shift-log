// Frontend logic for "Дневник смен водителя"

let state = {
  currentDate: null,
  availableDates: [],
  trips: [],
  summary: null,
};

// --- DOM Elements ---
const dateInput = document.getElementById('dateInput');
const dateHumanLabel = document.getElementById('dateHumanLabel');
const btnPrevDay = document.getElementById('btnPrevDay');
const btnNextDay = document.getElementById('btnNextDay');
const dateChipsContainer = document.getElementById('dateChipsContainer');

const kpiNetIncome = document.getElementById('kpiNetIncome');
const kpiRevenue = document.getElementById('kpiRevenue');
const kpiCommission = document.getElementById('kpiCommission');
const kpiCommissionRate = document.getElementById('kpiCommissionRate');
const kpiTripsCount = document.getElementById('kpiTripsCount');

const progressCard = document.getElementById('progressCard');
const progressCash = document.getElementById('progressCash');

const cardTripsCount = document.getElementById('cardTripsCount');
const cardRevenue = document.getElementById('cardRevenue');
const cardCommission = document.getElementById('cardCommission');
const cardNetIncome = document.getElementById('cardNetIncome');

const cashTripsCount = document.getElementById('cashTripsCount');
const cashRevenue = document.getElementById('cashRevenue');
const cashCommission = document.getElementById('cashCommission');
const cashNetIncome = document.getElementById('cashNetIncome');

const tripsList = document.getElementById('tripsList');
const emptyState = document.getElementById('emptyState');
const tripsSubheader = document.getElementById('tripsSubheader');

// Modal Elements
const addModal = document.getElementById('addModal');
const btnOpenAddModal = document.getElementById('btnOpenAddModal');
const btnCloseModal = document.getElementById('btnCloseModal');
const btnCancelModal = document.getElementById('btnCancelModal');
const btnEmptyAdd = document.getElementById('btnEmptyAdd');
const addTripForm = document.getElementById('addTripForm');
const formErrorBox = document.getElementById('formErrorBox');
const tripAmountInput = document.getElementById('tripAmount');
const tripCommissionInput = document.getElementById('tripCommission');
const tripStartInput = document.getElementById('tripStart');
const tripEndInput = document.getElementById('tripEnd');
const btnDemoDuplicate = document.getElementById('btnDemoDuplicate');
const toastEl = document.getElementById('toast');

// --- Helpers ---
function formatCurrency(num) {
  if (num === undefined || num === null) return '0 ₸';
  return Math.round(num).toLocaleString('ru-RU') + ' ₸';
}

function formatDateHuman(dateStr) {
  if (!dateStr) return '';
  const [year, month, day] = dateStr.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  return d.toLocaleDateString('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });
}

function formatTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function shiftDateString(dateStr, deltaDays) {
  const [year, month, day] = dateStr.split('-').map(Number);
  const d = new Date(year, month - 1, day + deltaDays);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function getTimezoneOffsetString() {
  const offsetMin = -new Date().getTimezoneOffset();
  const sign = offsetMin >= 0 ? '+' : '-';
  const absMin = Math.abs(offsetMin);
  const hours = String(Math.floor(absMin / 60)).padStart(2, '0');
  const mins = String(absMin % 60).padStart(2, '0');
  return `${sign}${hours}:${mins}`;
}

function showToast(message, type = 'info') {
  toastEl.textContent = message;
  toastEl.className = 'toast';
  if (type === 'success') toastEl.classList.add('toast-success');
  if (type === 'warning') toastEl.classList.add('toast-warning');
  toastEl.style.display = 'block';

  setTimeout(() => {
    toastEl.style.display = 'none';
  }, 4000);
}

// --- API Service Calls ---
async function fetchShiftData(dateStr) {
  try {
    const url = dateStr ? `/api/shift?date=${dateStr}` : '/api/shift';
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    state.currentDate = data.date;
    state.summary = data.summary;
    state.trips = data.trips;
    state.availableDates = data.available_dates;
    renderUI();
  } catch (err) {
    console.error('Ошибка загрузки данных смены:', err);
    showToast('Не удалось загрузить данные смены', 'warning');
  }
}

// --- Render UI ---
function renderUI() {
  // 1. Date Picker & human label
  dateInput.value = state.currentDate;
  dateHumanLabel.textContent = formatDateHuman(state.currentDate);

  // 2. Date chips
  renderDateChips();

  // 3. KPI Cards
  const sum = state.summary || {};
  kpiNetIncome.textContent = formatCurrency(sum.net_income);
  kpiRevenue.textContent = formatCurrency(sum.revenue);
  kpiCommission.textContent = formatCurrency(sum.commission);
  kpiTripsCount.textContent = sum.trips_count || 0;

  if (sum.revenue > 0) {
    const rate = ((sum.commission / sum.revenue) * 100).toFixed(1);
    kpiCommissionRate.textContent = `${rate}% от выручки`;
  } else {
    kpiCommissionRate.textContent = 'Парк и сервис';
  }

  // 4. Breakdown Cards
  const card = sum.card || {};
  const cash = sum.cash || {};

  cardTripsCount.textContent = card.trips_count || 0;
  cardRevenue.textContent = formatCurrency(card.revenue);
  cardCommission.textContent = formatCurrency(card.commission);
  cardNetIncome.textContent = formatCurrency(card.net_income);

  cashTripsCount.textContent = cash.trips_count || 0;
  cashRevenue.textContent = formatCurrency(cash.revenue);
  cashCommission.textContent = formatCurrency(cash.commission);
  cashNetIncome.textContent = formatCurrency(cash.net_income);

  // Progress Bar
  const totalRev = (card.revenue || 0) + (cash.revenue || 0);
  if (totalRev > 0) {
    const cardPct = Math.round((card.revenue / totalRev) * 100);
    const cashPct = 100 - cardPct;
    progressCard.style.width = `${cardPct}%`;
    progressCash.style.width = `${cashPct}%`;
  } else {
    progressCard.style.width = '50%';
    progressCash.style.width = '50%';
  }

  // 5. Trips List
  renderTripsList();
}

function renderDateChips() {
  dateChipsContainer.innerHTML = '';
  // Show available shift dates
  const dates = [...state.availableDates];
  if (!dates.includes(state.currentDate)) {
    dates.push(state.currentDate);
    dates.sort();
  }

  dates.forEach(d => {
    const btn = document.createElement('button');
    btn.className = `date-chip ${d === state.currentDate ? 'active' : ''}`;
    const [_, m, day] = d.split('-');
    const months = ['', 'янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
    btn.textContent = `${parseInt(day, 10)} ${months[parseInt(m, 10)]}`;
    btn.onclick = () => {
      fetchShiftData(d);
    };
    dateChipsContainer.appendChild(btn);
  });
}

function renderTripsList() {
  tripsList.innerHTML = '';
  const trips = state.trips || [];
  tripsSubheader.textContent = `Показано: ${trips.length} ${getNounTrips(trips.length)}`;

  if (trips.length === 0) {
    emptyState.style.display = 'block';
    tripsList.style.display = 'none';
    return;
  }

  emptyState.style.display = 'none';
  tripsList.style.display = 'flex';

  trips.forEach(t => {
    const item = document.createElement('div');
    item.className = 'trip-item-card';

    const startTime = formatTime(t.start);
    const endTime = formatTime(t.end);
    const startDt = new Date(t.start);
    const endDt = new Date(t.end);
    const durationMin = Math.round((endDt - startDt) / 60000);

    const isCard = t.payment === 'card';
    const paymentBadgeHtml = isCard
      ? `<span class="trip-payment-badge badge-card">💳 Карта</span>`
      : `<span class="trip-payment-badge badge-cash">💵 Наличные</span>`;

    const net = Math.round(t.amount - t.commission);

    item.innerHTML = `
      <div class="trip-left">
        <span class="trip-badge-id">#${escapeHtml(t.id)}</span>
        <div class="trip-time-info">
          <div class="trip-times">${startTime} – ${endTime}</div>
          <div class="trip-duration">${durationMin} мин</div>
        </div>
        ${paymentBadgeHtml}
      </div>
      <div class="trip-right">
        <div class="trip-amount">${formatCurrency(t.amount)}</div>
        <div class="trip-net-formula">
          Комиссия: -${formatCurrency(t.commission)} | 
          <span class="trip-net-bold">«на руки»: ${formatCurrency(net)}</span>
        </div>
      </div>
    `;
    tripsList.appendChild(item);
  });
}

function getNounTrips(count) {
  const rem10 = count % 10;
  const rem100 = count % 100;
  if (rem100 >= 11 && rem100 <= 19) return 'поездок';
  if (rem10 === 1) return 'поездка';
  if (rem10 >= 2 && rem10 <= 4) return 'поездки';
  return 'поездок';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// --- Event Listeners ---
dateInput.addEventListener('change', (e) => {
  if (e.target.value) {
    fetchShiftData(e.target.value);
  }
});

btnPrevDay.addEventListener('click', () => {
  if (state.currentDate) {
    const prev = shiftDateString(state.currentDate, -1);
    fetchShiftData(prev);
  }
});

btnNextDay.addEventListener('click', () => {
  if (state.currentDate) {
    const next = shiftDateString(state.currentDate, 1);
    fetchShiftData(next);
  }
});

// Modal Logic
function openAddModal() {
  formErrorBox.style.display = 'none';
  formErrorBox.textContent = '';
  addTripForm.reset();

  // Set default times matching selected day
  const baseDate = state.currentDate || new Date().toISOString().slice(0, 10);
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  
  tripStartInput.value = `${baseDate}T${hh}:${mm}`;
  // Default end + 25 mins
  const endD = new Date(now.getTime() + 25 * 60000);
  const endHh = String(endD.getHours()).padStart(2, '0');
  const endMm = String(endD.getMinutes()).padStart(2, '0');
  tripEndInput.value = `${baseDate}T${endHh}:${endMm}`;

  addModal.style.display = 'flex';
}

function closeModal() {
  addModal.style.display = 'none';
}

btnOpenAddModal.addEventListener('click', openAddModal);
btnEmptyAdd.addEventListener('click', openAddModal);
btnCloseModal.addEventListener('click', closeModal);
btnCancelModal.addEventListener('click', closeModal);

// Quick duration chips
document.querySelectorAll('.btn-chip').forEach(btn => {
  btn.addEventListener('click', () => {
    const min = parseInt(btn.dataset.min, 10);
    if (!tripStartInput.value) return;
    const start = new Date(tripStartInput.value);
    const end = new Date(start.getTime() + min * 60000);
    const yyyy = end.getFullYear();
    const MM = String(end.getMonth() + 1).padStart(2, '0');
    const dd = String(end.getDate()).padStart(2, '0');
    const hh = String(end.getHours()).padStart(2, '0');
    const mm = String(end.getMinutes()).padStart(2, '0');
    tripEndInput.value = `${yyyy}-${MM}-${dd}T${hh}:${mm}`;
  });
});

// Auto-calculate default 15% commission on amount change
tripAmountInput.addEventListener('input', () => {
  const val = parseFloat(tripAmountInput.value);
  if (!isNaN(val) && val > 0 && (!tripCommissionInput.value || tripCommissionInput.value === '0')) {
    tripCommissionInput.value = (val * 0.15).toFixed(0);
  }
});

// Submit Form
addTripForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  formErrorBox.style.display = 'none';

  const startVal = tripStartInput.value;
  const endVal = tripEndInput.value;
  const amount = parseFloat(tripAmountInput.value);
  const commission = parseFloat(tripCommissionInput.value);
  const payment = document.querySelector('input[name="tripPayment"]:checked').value;
  const tripId = document.getElementById('tripId').value.trim() || undefined;

  // Client-side validations
  if (isNaN(amount) || amount <= 0) {
    showFormError('Сумма поездки должна быть больше 0 ₸.');
    return;
  }
  if (new Date(endVal) <= new Date(startVal)) {
    showFormError('Время окончания поездки должно быть строго позже времени начала!');
    return;
  }
  if (isNaN(commission) || commission < 0) {
    showFormError('Комиссия должна быть не меньше 0 ₸.');
    return;
  }
  if (commission > amount) {
    showFormError('Комиссия не может превышать сумму поездки!');
    return;
  }

  // Format with timezone offset
  const tzOffset = getTimezoneOffsetString();
  const payload = {
    start: `${startVal}:00${tzOffset}`,
    end: `${endVal}:00${tzOffset}`,
    amount,
    commission,
    payment,
  };
  if (tripId) payload.id = tripId;

  try {
    const res = await fetch('/api/trips', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      const errMsg = (data.detail && typeof data.detail === 'string')
        ? data.detail
        : (data.detail?.[0]?.msg || 'Ошибка валидации сервера');
      showFormError(errMsg);
      return;
    }

    closeModal();
    if (data.is_duplicate) {
      showToast(`⚠️ Поездка #${data.trip.id} уже была сохранена ранее. Дубль предотвращен!`, 'warning');
    } else {
      showToast(`✅ Поездка #${data.trip.id} успешно добавлена!`, 'success');
    }

    // Refresh data for the trip's date
    const tripDate = startVal.slice(0, 10);
    fetchShiftData(tripDate);
  } catch (err) {
    showFormError('Сетевая ошибка при сохранении поездки: ' + err.message);
  }
});

function showFormError(msg) {
  formErrorBox.textContent = msg;
  formErrorBox.style.display = 'block';
}

// Test Duplicate Protection Demo button
btnDemoDuplicate.addEventListener('click', async () => {
  // Sends identical trip t1 to demonstrate duplicate prevention
  const payload = {
    id: "t1",
    start: "2026-10-01T08:10:00+05:00",
    end: "2026-10-01T08:32:00+05:00",
    amount: 2400.0,
    payment: "card",
    commission: 360.0
  };

  try {
    const res = await fetch('/api/trips', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.is_duplicate) {
      showToast(`🛡 Защита сработала! Поездка #${data.trip.id} распознана как дубль. Лишняя запись не создана.`, 'warning');
    } else {
      showToast(`Поездка сохранена: #${data.trip.id}`, 'success');
      fetchShiftData('2026-10-01');
    }
  } catch (err) {
    showToast('Ошибка при отправке запроса', 'warning');
  }
});

// Initial boot
fetchShiftData();
