/**
 * Scholarship Management System - Single Page Frontend
 * Communicates with FastAPI backend on Render
 */

const apiUrl = (window.SCHOLARSHIP_API_URL || "").replace(/\/$/, "");
const money = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

// State cache
let cachedInstitutes = [];
let cachedStudents = [];
let cachedScholarships = [];

// DOM Elements
const toastContainer = document.getElementById("toast-container");
const apiStatus = document.getElementById("api-status");
const pageTitle = document.getElementById("page-title");
const pageEyebrow = document.getElementById("page-eyebrow");

// Tab Title Config
const tabConfig = {
  dashboard: { title: "Overview", eyebrow: "ADMINISTRATION PANEL" },
  students: { title: "Students Directory", eyebrow: "STUDENT RECORDS" },
  scholarships: { title: "Scholarship Schemes", eyebrow: "SCHOLARSHIP CATALOGUE" },
  applications: { title: "Application Workflow", eyebrow: "REVIEW & DECISIONS" },
  disbursements: { title: "Disbursement Register", eyebrow: "FINANCIAL DISBURSEMENTS" },
  institutes: { title: "Institute Analytics", eyebrow: "INSTITUTE ALLOCATIONS" }
};

// ---------------------------------------------------------------------------
// Toast Notifications
// ---------------------------------------------------------------------------
function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.25s ease";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// ---------------------------------------------------------------------------
// Navigation & Routing
// ---------------------------------------------------------------------------
function switchTab(tabName, filterValue = null) {
  if (!tabConfig[tabName]) tabName = "dashboard";

  // Update URL hash without extra history spam
  if (window.location.hash !== `#${tabName}`) {
    window.location.hash = tabName;
  }

  // Update Nav links
  document.querySelectorAll("#sidebar-nav a").forEach(a => {
    a.classList.toggle("selected", a.dataset.tab === tabName);
  });

  // Update Header
  pageTitle.textContent = tabConfig[tabName].title;
  pageEyebrow.textContent = tabConfig[tabName].eyebrow;

  // Toggle Tab Views
  document.querySelectorAll(".tab-view").forEach(view => {
    view.classList.toggle("active", view.id === `view-${tabName}`);
  });

  // Trigger data loader
  switch (tabName) {
    case "dashboard":
      loadDashboard();
      break;
    case "students":
      if (filterValue) {
        const filterSelect = document.getElementById("student-institute-filter");
        if (filterSelect) filterSelect.value = filterValue;
      }
      loadStudents();
      break;
    case "scholarships":
      loadScholarships();
      break;
    case "applications":
      if (filterValue) {
        const filterSelect = document.getElementById("app-institute-filter");
        if (filterSelect) filterSelect.value = filterValue;
      }
      loadApplications();
      break;
    case "disbursements":
      loadDisbursements();
      break;
    case "institutes":
      loadInstitutes();
      break;
  }
}

// Listen to Hash Change
window.addEventListener("hashchange", () => {
  const tab = window.location.hash.replace("#", "") || "dashboard";
  switchTab(tab);
});

// Setup click listeners for nav items
document.querySelectorAll("#sidebar-nav a").forEach(a => {
  a.addEventListener("click", e => {
    e.preventDefault();
    switchTab(a.dataset.tab);
  });
});

// Setup click listeners for dashboard metric cards
document.querySelectorAll(".stat-card[data-goto]").forEach(card => {
  card.addEventListener("click", () => {
    switchTab(card.dataset.goto);
  });
});

// ---------------------------------------------------------------------------
// Helper Fetch with error formatting
// ---------------------------------------------------------------------------
async function apiFetch(endpoint, options = {}) {
  const response = await fetch(`${apiUrl}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const errorMsg = data?.detail || data?.message || "An unexpected error occurred.";
    throw new Error(errorMsg);
  }
  return data;
}

// ---------------------------------------------------------------------------
// TAB 1: DASHBOARD
// ---------------------------------------------------------------------------
async function loadDashboard() {
  try {
    const [dashData, instData] = await Promise.all([
      apiFetch("/api/dashboard"),
      apiFetch("/api/institutes").catch(() => ({ institutes: [] }))
    ]);

    // Totals
    document.getElementById("dash-students").textContent = dashData.totals.students;
    document.getElementById("dash-scholarships").textContent = dashData.totals.scholarships;
    document.getElementById("dash-applications").textContent = dashData.totals.applications;
    document.getElementById("dash-paid").textContent = dashData.totals.paid;

    // Recent applications table
    const tbody = document.getElementById("dash-recent-table");
    if (!dashData.recent || dashData.recent.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="muted-cell">No recent applications submitted yet.</td></tr>`;
    } else {
      tbody.innerHTML = dashData.recent.map(item => `
        <tr>
          <td><b>${escapeHtml(item.student_name)}</b><br><small>${item.apply_date}</small></td>
          <td>${escapeHtml(item.institute || "—")}</td>
          <td>${escapeHtml(item.scholarship_name)}</td>
          <td>₹${money.format(item.amount)}</td>
          <td><span class="badge ${item.status.toLowerCase()}">${item.status}</span></td>
        </tr>
      `).join("");
    }

    // Status progress
    const totalApps = dashData.totals.applications || 1;
    const statusContainer = document.getElementById("dash-status-list");
    statusContainer.innerHTML = (dashData.status_counts || []).map(item => `
      <div class="progress">
        <div><span>${item.status}</span><b>${item.total}</b></div>
        <i class="${item.status.toLowerCase()}" style="width:${(item.total / totalApps) * 100}%"></i>
      </div>
    `).join("");

    // Participating institutes snapshot
    const instBody = document.getElementById("dash-institutes-table");
    if (!instData.institutes || instData.institutes.length === 0) {
      instBody.innerHTML = `<tr><td colspan="5" class="muted-cell">No institutes registered.</td></tr>`;
    } else {
      instBody.innerHTML = instData.institutes.map(inst => `
        <tr>
          <td><b>${escapeHtml(inst.institute)}</b></td>
          <td>${inst.total_students}</td>
          <td>${inst.total_applications}</td>
          <td><span class="badge approved">${inst.approved_applications}</span></td>
          <td><b>₹${money.format(inst.total_disbursed)}</b></td>
        </tr>
      `).join("");
    }

    if (apiStatus) {
      apiStatus.textContent = "Service status: Online (FastAPI)";
      apiStatus.className = "api-status online";
    }
  } catch (error) {
    console.error("Dashboard load failed:", error);
    if (apiStatus) {
      apiStatus.textContent = "Service status: Disconnected";
      apiStatus.className = "api-status offline";
    }
    showToast("Could not load dashboard data from backend.", "error");
  }
}

// ---------------------------------------------------------------------------
// TAB 2: STUDENTS
// ---------------------------------------------------------------------------
async function loadStudents() {
  const search = document.getElementById("student-search").value.trim();
  const instFilter = document.getElementById("student-institute-filter").value;

  let query = `/api/students?`;
  if (instFilter && instFilter !== "all") query += `institute=${encodeURIComponent(instFilter)}&`;
  if (search) query += `search=${encodeURIComponent(search)}&`;

  try {
    const data = await apiFetch(query);
    cachedStudents = data.students || [];

    // Populate Institute Filter & Datalist
    if (data.institutes) {
      cachedInstitutes = data.institutes;
      updateInstituteDropdowns(data.institutes);
    }

    const tbody = document.getElementById("students-table-body");
    if (cachedStudents.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="muted-cell">No students found matching your criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = cachedStudents.map(s => `
      <tr>
        <td>#${s.student_id}</td>
        <td><b>${escapeHtml(s.student_name)}</b></td>
        <td><code>${s.aadhaar_no}</code></td>
        <td>${escapeHtml(s.institute)}<br><small>${escapeHtml(s.course)}</small></td>
        <td>₹${money.format(s.income)}</td>
        <td>
          <button class="btn-delete" onclick="handleDeleteStudent(${s.student_id}, '${escapeHtml(s.student_name)}')">Delete</button>
        </td>
      </tr>
    `).join("");
  } catch (error) {
    showToast(error.message, "error");
  }
}

function updateInstituteDropdowns(institutes) {
  // Update students filter
  const stuFilter = document.getElementById("student-institute-filter");
  const currentStuVal = stuFilter.value;
  stuFilter.innerHTML = `<option value="all">All Institutes</option>` +
    institutes.map(inst => `<option value="${escapeHtml(inst)}" ${inst === currentStuVal ? "selected" : ""}>${escapeHtml(inst)}</option>`).join("");

  // Update datalist for add student form
  const datalist = document.getElementById("institute-datalist");
  datalist.innerHTML = institutes.map(inst => `<option value="${escapeHtml(inst)}">`).join("");

  // Update applications institute filter
  const appFilter = document.getElementById("app-institute-filter");
  if (appFilter) {
    const currentAppVal = appFilter.value;
    appFilter.innerHTML = `<option value="all">All Institutes</option>` +
      institutes.map(inst => `<option value="${escapeHtml(inst)}" ${inst === currentAppVal ? "selected" : ""}>${escapeHtml(inst)}</option>`).join("");
  }
}

// Student Search & Filter Listeners
document.getElementById("student-search").addEventListener("input", debounce(loadStudents, 250));
document.getElementById("student-institute-filter").addEventListener("change", loadStudents);

// Toggle Student Form
document.getElementById("toggle-student-form-btn").addEventListener("click", () => {
  const panel = document.getElementById("student-form-panel");
  panel.classList.toggle("collapsed");
  if (!panel.classList.contains("collapsed")) {
    document.getElementById("stu-name").focus();
  }
});

// Aadhaar Length Counter
document.getElementById("stu-aadhaar").addEventListener("input", function() {
  const counter = document.getElementById("aadhaar-counter");
  const len = this.value.length;
  counter.textContent = `${len}/12`;
  counter.style.color = len === 12 ? "var(--green)" : "var(--muted)";
});

// Add Student Form Submit
document.getElementById("add-student-form").addEventListener("submit", async function(e) {
  e.preventDefault();
  const btn = document.getElementById("save-student-btn");
  btn.disabled = true;
  btn.textContent = "Saving…";

  const payload = {
    student_name: document.getElementById("stu-name").value.trim(),
    aadhaar_no: document.getElementById("stu-aadhaar").value.trim(),
    institute: document.getElementById("stu-institute").value.trim(),
    course: document.getElementById("stu-course").value.trim(),
    income: parseFloat(document.getElementById("stu-income").value) || 0
  };

  try {
    const res = await apiFetch("/api/students", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(res.message || "Student registered successfully!");
    this.reset();
    document.getElementById("aadhaar-counter").textContent = "0/12";
    document.getElementById("student-form-panel").classList.add("collapsed");
    loadStudents();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Save Student";
  }
});

// Delete Student Handler
window.handleDeleteStudent = async function(id, name) {
  if (!confirm(`Are you sure you want to delete student "${name}"?`)) return;
  try {
    const res = await apiFetch(`/api/students/${id}`, { method: "DELETE" });
    showToast(res.message || "Student removed.");
    loadStudents();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ---------------------------------------------------------------------------
// TAB 3: SCHOLARSHIPS
// ---------------------------------------------------------------------------
async function loadScholarships() {
  try {
    const data = await apiFetch("/api/scholarships");
    cachedScholarships = data.scholarships || [];

    const grid = document.getElementById("scholarships-grid");
    if (cachedScholarships.length === 0) {
      grid.innerHTML = `<div class="muted-cell">No scholarship schemes available. Create one using the form above!</div>`;
      return;
    }

    grid.innerHTML = cachedScholarships.map(sc => `
      <article class="scholar-card">
        <div>
          <p class="eyebrow">DEADLINE: ${sc.deadline}</p>
          <h3>${escapeHtml(sc.scholarship_name)}</h3>
          <p class="eligibility">${escapeHtml(sc.eligibility)}</p>
        </div>
        <div class="scholar-card-footer">
          <div>
            <span class="scholar-amount">₹${money.format(sc.amount)}</span>
            <span class="scholar-applicants-tag">${sc.applications_count || 0} applied · ${sc.approved_count || 0} approved</span>
          </div>
          <button class="btn btn-primary btn-sm" onclick="applyForScholarship(${sc.scholarship_id})">Apply →</button>
        </div>
      </article>
    `).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Add Scholarship Form Submit
document.getElementById("add-scholarship-form").addEventListener("submit", async function(e) {
  e.preventDefault();
  const btn = document.getElementById("save-scholarship-btn");
  btn.disabled = true;
  btn.textContent = "Creating…";

  const payload = {
    scholarship_name: document.getElementById("sc-name").value.trim(),
    eligibility: document.getElementById("sc-eligibility").value.trim(),
    amount: parseFloat(document.getElementById("sc-amount").value) || 0,
    deadline: document.getElementById("sc-deadline").value
  };

  try {
    const res = await apiFetch("/api/scholarships", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(res.message || "Scholarship programme created!");
    this.reset();
    loadScholarships();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Create Scheme";
  }
});

// Quick shortcut from scholarship card to application form
window.applyForScholarship = function(scholarshipId) {
  switchTab("applications");
  setTimeout(() => {
    document.getElementById("app-form-panel").classList.remove("collapsed");
    const select = document.getElementById("app-scholarship-select");
    if (select) select.value = scholarshipId;
  }, 100);
};

// ---------------------------------------------------------------------------
// TAB 4: APPLICATIONS
// ---------------------------------------------------------------------------
async function loadApplications() {
  const statusFilter = document.getElementById("app-status-filter").value;
  const instFilter = document.getElementById("app-institute-filter").value;

  let query = `/api/applications?`;
  if (statusFilter && statusFilter !== "all") query += `status=${encodeURIComponent(statusFilter)}&`;
  if (instFilter && instFilter !== "all") query += `institute=${encodeURIComponent(instFilter)}&`;

  try {
    const [appData, studentsData, scholarshipsData] = await Promise.all([
      apiFetch(query),
      apiFetch("/api/students"),
      apiFetch("/api/scholarships")
    ]);

    // Populate dropdowns for new application form
    const studentSelect = document.getElementById("app-student-select");
    studentSelect.innerHTML = `<option value="">Select applicant student…</option>` +
      (studentsData.students || []).map(s => `
        <option value="${s.student_id}">${escapeHtml(s.student_name)} (${escapeHtml(s.institute)})</option>
      `).join("");

    const scholarshipSelect = document.getElementById("app-scholarship-select");
    scholarshipSelect.innerHTML = `<option value="">Select scholarship scheme…</option>` +
      (scholarshipsData.scholarships || []).map(sc => `
        <option value="${sc.scholarship_id}">${escapeHtml(sc.scholarship_name)} (₹${money.format(sc.amount)})</option>
      `).join("");

    // Set today as default date if empty
    const dateInput = document.getElementById("app-date");
    if (!dateInput.value) {
      dateInput.value = new Date().toISOString().split("T")[0];
    }

    // Populate table
    const tbody = document.getElementById("applications-table-body");
    const apps = appData.applications || [];
    if (apps.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="muted-cell">No applications found matching the selected criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = apps.map(app => {
      const isApproved = app.status === "Approved";
      const isRejected = app.status === "Rejected";

      let actionButtons = "";
      if (app.status === "Pending") {
        actionButtons = `
          <button class="btn btn-sm btn-approve" onclick="updateAppStatus(${app.application_id}, 'Approved')">Approve</button>
          <button class="btn btn-sm btn-reject" onclick="updateAppStatus(${app.application_id}, 'Rejected')">Reject</button>
        `;
      } else if (isApproved) {
        actionButtons = `
          <button class="btn btn-sm btn-reject" onclick="updateAppStatus(${app.application_id}, 'Rejected')">Reject</button>
          <button class="btn btn-sm btn-reset" onclick="updateAppStatus(${app.application_id}, 'Pending')">Reset</button>
        `;
      } else {
        actionButtons = `
          <button class="btn btn-sm btn-approve" onclick="updateAppStatus(${app.application_id}, 'Approved')">Approve</button>
          <button class="btn btn-sm btn-reset" onclick="updateAppStatus(${app.application_id}, 'Pending')">Reset</button>
        `;
      }

      return `
        <tr>
          <td>#${app.application_id}</td>
          <td><b>${escapeHtml(app.student_name)}</b><br><small>${escapeHtml(app.institute)}</small></td>
          <td>${escapeHtml(app.scholarship_name)}</td>
          <td>₹${money.format(app.amount)}</td>
          <td>${app.apply_date}</td>
          <td><span class="badge ${app.status.toLowerCase()}">${app.status}</span></td>
          <td>${actionButtons}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Application Filters
document.getElementById("app-status-filter").addEventListener("change", loadApplications);
document.getElementById("app-institute-filter").addEventListener("change", loadApplications);

// Toggle Application Form
document.getElementById("toggle-app-form-btn").addEventListener("click", () => {
  const panel = document.getElementById("app-form-panel");
  panel.classList.toggle("collapsed");
});

// Update Application Status
window.updateAppStatus = async function(appId, newStatus) {
  try {
    const res = await apiFetch(`/api/applications/${appId}/status`, {
      method: "POST",
      body: JSON.stringify({ status: newStatus })
    });
    showToast(res.message || `Status updated to ${newStatus}`);
    loadApplications();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// Submit Application Form
document.getElementById("add-application-form").addEventListener("submit", async function(e) {
  e.preventDefault();
  const btn = document.getElementById("save-application-btn");
  btn.disabled = true;
  btn.textContent = "Submitting…";

  const payload = {
    student_id: parseInt(document.getElementById("app-student-select").value),
    scholarship_id: parseInt(document.getElementById("app-scholarship-select").value),
    apply_date: document.getElementById("app-date").value
  };

  try {
    const res = await apiFetch("/api/applications", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(res.message || "Application submitted successfully!");
    this.reset();
    document.getElementById("app-form-panel").classList.add("collapsed");
    loadApplications();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Submit Application";
  }
});

// ---------------------------------------------------------------------------
// TAB 5: DISBURSEMENTS
// ---------------------------------------------------------------------------
async function loadDisbursements() {
  try {
    const data = await apiFetch("/api/disbursements");

    // Metrics
    document.getElementById("disb-total-amount").textContent = `₹${money.format(data.total_disbursed_amount || 0)}`;
    document.getElementById("disb-unpaid-count").textContent = (data.approved_unpaid || []).length;
    document.getElementById("disb-paid-count").textContent = (data.disbursements || []).length;

    // Populate approved unpaid applications dropdown
    const select = document.getElementById("disb-application-select");
    const unpaid = data.approved_unpaid || [];
    if (unpaid.length === 0) {
      select.innerHTML = `<option value="">No approved applications awaiting disbursement</option>`;
    } else {
      select.innerHTML = `<option value="">Select approved application…</option>` +
        unpaid.map(a => `
          <option value="${a.application_id}">#${a.application_id} — ${escapeHtml(a.student_name)} (${escapeHtml(a.institute)}) — ₹${money.format(a.amount)}</option>
        `).join("");
    }

    // Set today as payment date
    const dateInput = document.getElementById("disb-date");
    if (!dateInput.value) {
      dateInput.value = new Date().toISOString().split("T")[0];
    }

    // Suggest a random transaction ref if empty
    const refInput = document.getElementById("disb-ref");
    if (!refInput.value) {
      const year = new Date().getFullYear();
      const rand = Math.floor(1000 + Math.random() * 9000);
      refInput.value = `TXN-${year}-${rand}`;
    }

    // Populate table
    const tbody = document.getElementById("disbursements-table-body");
    const disbList = data.disbursements || [];
    if (disbList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="muted-cell">No disbursements recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = disbList.map(d => `
      <tr>
        <td>#${d.disbursement_id}</td>
        <td><b>${escapeHtml(d.student_name)}</b></td>
        <td>${escapeHtml(d.institute || "—")}</td>
        <td>${escapeHtml(d.scholarship_name)}</td>
        <td><b>₹${money.format(d.amount)}</b></td>
        <td>${d.payment_date}</td>
        <td><code>${escapeHtml(d.transaction_ref)}</code></td>
        <td><span class="badge ${d.status.toLowerCase()}">${d.status}</span></td>
      </tr>
    `).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Add Disbursement Form Submit
document.getElementById("add-disbursement-form").addEventListener("submit", async function(e) {
  e.preventDefault();
  const btn = document.getElementById("save-disbursement-btn");
  btn.disabled = true;
  btn.textContent = "Recording…";

  const payload = {
    application_id: parseInt(document.getElementById("disb-application-select").value),
    payment_date: document.getElementById("disb-date").value,
    status: document.getElementById("disb-status").value,
    transaction_ref: document.getElementById("disb-ref").value.trim()
  };

  try {
    const res = await apiFetch("/api/disbursements", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(res.message || "Disbursement recorded successfully!");
    this.reset();
    loadDisbursements();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Record Payment";
  }
});

// ---------------------------------------------------------------------------
// TAB 6: INSTITUTES
// ---------------------------------------------------------------------------
async function loadInstitutes() {
  try {
    const data = await apiFetch("/api/institutes");
    const institutes = data.institutes || [];

    const tbody = document.getElementById("institutes-table-body");
    if (institutes.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="muted-cell">No institutes with student records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = institutes.map(inst => {
      const appCount = inst.total_applications || 0;
      const approvedCount = inst.approved_applications || 0;
      const rate = appCount > 0 ? Math.round((approvedCount / appCount) * 100) : 0;

      return `
        <tr>
          <td><b>${escapeHtml(inst.institute)}</b></td>
          <td><b>${inst.total_students}</b></td>
          <td>${inst.total_applications}</td>
          <td><span class="badge approved">${inst.approved_applications}</span></td>
          <td><span class="badge pending">${inst.pending_applications}</span></td>
          <td><span class="badge rejected">${inst.rejected_applications}</span></td>
          <td>${rate}%</td>
          <td><b>₹${money.format(inst.total_disbursed)}</b></td>
          <td>
            <button class="btn btn-sm btn-primary" onclick="viewInstituteStudents('${escapeHtml(inst.institute)}')">View Students →</button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

window.viewInstituteStudents = function(instName) {
  switchTab("students", instName);
};

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function debounce(fn, delay) {
  let timer = null;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

// ---------------------------------------------------------------------------
// Initial Boot
// ---------------------------------------------------------------------------
const initialTab = window.location.hash.replace("#", "") || "dashboard";
switchTab(initialTab);
