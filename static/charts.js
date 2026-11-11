(() => {
  const data = window.dashboardData;
  if (!data || !window.Chart || !data.chartMode) return;

  Chart.defaults.font.family = "'Prompt', sans-serif";
  Chart.defaults.color = "#66615d";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  const colors = ["#e86f25", "#536d8a", "#72a18b"];
  const grid = "rgba(60, 55, 50, .10)";

  function makeTrendChart(id, rows) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const labels = rows.map(row => row.year);
    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "ตอนที่ 3 · ผลลัพธ์หลักสูตร", data: rows.map(row => row.section3), backgroundColor: colors[0], borderRadius: 5, maxBarThickness: 30 },
          { label: "ตอนที่ 4 · สมรรถนะ 5 ด้าน", data: rows.map(row => row.section4), backgroundColor: colors[1], borderRadius: 5, maxBarThickness: 30 },
          { label: "ภาพรวมตอนที่ 3–4", data: rows.map(row => row.overall), backgroundColor: colors[2], borderRadius: 5, maxBarThickness: 30 },
          { type: "line", label: "เป้าหมาย 80%", data: labels.map(() => 80), borderColor: "#bd4d43", borderDash: [7, 5], pointRadius: 0, borderWidth: 2 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", align: "start" },
          tooltip: {
            callbacks: {
              afterTitle: items => {
                const row = rows[items[0]?.dataIndex];
                return row ? `จำนวนแบบประเมิน n = ${row.n}` : "";
              },
              label: context => context.parsed.y == null ? " ไม่มีข้อมูล" : ` ${context.dataset.label}: ${context.parsed.y}%`,
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxRotation: 0, minRotation: 0 } },
          y: { beginAtZero: true, max: 100, grid: { color: grid }, ticks: { callback: value => value + "%" } },
        },
      },
    });
  }

  makeTrendChart("masterTrendChart", data.master || []);
  makeTrendChart("doctorateTrendChart", data.doctorate || []);
})();
