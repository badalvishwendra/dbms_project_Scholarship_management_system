const apiUrl = window.SCHOLARSHIP_API_URL.replace(/\/$/, "");
const money = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

async function loadDashboard() {
  const status = document.querySelector("#api-status");
  try {
    const response = await fetch(`${apiUrl}/api/dashboard`);
    if (!response.ok) throw new Error("The API returned an error.");
    const data = await response.json();
    for (const key of ["students", "scholarships", "applications", "paid"]) {
      document.querySelector(`#${key}`).textContent = data.totals[key];
    }
    document.querySelector("#recent").innerHTML = data.recent.map(item => `
      <tr><td><b>${item.student_name}</b><br><small>${item.apply_date}</small></td>
      <td>${item.scholarship_name}</td><td>₹${money.format(item.amount)}</td>
      <td><span class="badge ${item.status.toLowerCase()}">${item.status}</span></td></tr>`).join("");
    document.querySelector("#status-list").innerHTML = data.status_counts.map(item => `
      <div class="progress"><div><span>${item.status}</span><b>${item.total}</b></div>
      <i class="${item.status.toLowerCase()}" style="width:${(item.total / data.totals.applications) * 100}%"></i></div>`).join("");
    status.textContent = "Service status: Active";
    status.classList.add("online");
  } catch (error) {
    status.textContent = "Service status: Offline — start the backend or update config.js.";
    console.error(error);
  }
}
loadDashboard();
