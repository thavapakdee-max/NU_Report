(() => {
  const data = window.dashboardData;
  if (!data || !window.Chart) return;
  Chart.defaults.font.family = "'Prompt', sans-serif";
  Chart.defaults.color = "#66615d";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  const grid = "rgba(60, 55, 50, .10)";

  if (data.reportMode) {
    const canvas = document.getElementById("facultyChart");
    if (!canvas) return;
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: data.faculties.map(row => row.name),
        datasets: [{
          label: "อัตราตอบกลับ (%)",
          data: data.faculties.map(row => row.rate),
          backgroundColor: "#e86f25",
          borderRadius: 7,
          maxBarThickness: 58,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: context => " " + context.parsed.y + "%" } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxRotation: 0, minRotation: 0 } },
          y: { beginAtZero: true, max: 100, grid: { color: grid }, ticks: { callback: value => value + "%" } },
        },
      },
    });
    return;
  }

  const canvas = document.getElementById("departmentChart");
  if (!canvas) return;
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.departments.map(row => row.name),
      datasets: [
        { label: "บัณฑิตทั้งหมด", data: data.departments.map(row => row.graduates), backgroundColor: "#d8d5d1", borderRadius: 5, maxBarThickness: 32 },
        { label: "ประเมินแล้ว", data: data.departments.map(row => row.completed), backgroundColor: "#e86f25", borderRadius: 5, maxBarThickness: 32 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", align: "start" } },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, minRotation: 0 } },
        y: { beginAtZero: true, suggestedMax: 5, precision: 0, grid: { color: grid } },
      },
    },
  });
})();
