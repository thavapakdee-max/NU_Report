(() => {
  const form = document.querySelector("[data-survey-wizard]");
  if (!form) return;

  const steps = Array.from(form.querySelectorAll(".survey-step"));
  const titles = [
    "ตอนที่ 1 · ข้อมูลผู้ประเมิน",
    "ตอนที่ 2 · ข้อมูลบัณฑิต",
    "ตอนที่ 3 · ผลการเรียนรู้ตามหลักสูตร",
    "ตอนที่ 4 · สมรรถนะหลัก",
    "ตอนที่ 5 · ข้อคิดเห็นและข้อเสนอแนะ",
  ];
  const progress = document.getElementById("progressFill");
  const stepTitle = document.getElementById("stepTitle");
  const stepCount = document.getElementById("stepCount");
  const previous = document.getElementById("previousStep");
  const next = document.getElementById("nextStep");
  const submit = document.getElementById("submitEvaluation");
  let current = 0;

  function showStep(index) {
    current = index;
    steps.forEach((step, i) => { step.hidden = i !== index; });
    stepTitle.textContent = titles[index];
    stepCount.textContent = (index + 1) + " / " + steps.length;
    progress.style.width = (((index + 1) / steps.length) * 100) + "%";
    previous.hidden = index === 0;
    next.hidden = index === steps.length - 1;
    submit.hidden = index !== steps.length - 1;
    if (index === steps.length - 1) updateReview();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function validateCurrentStep() {
    if (form.dataset.preview === "true") return true;
    const controls = Array.from(steps[current].querySelectorAll("input, select, textarea"));
    for (const control of controls) {
      if (control.willValidate && !control.checkValidity()) {
        control.reportValidity();
        control.focus({ preventScroll: false });
        return false;
      }
    }
    return true;
  }

  if (form.dataset.preview === "true") {
    form.addEventListener("submit", (event) => event.preventDefault());
  }

  function updateGraduatePreview() {
    const select = document.getElementById("graduateSelect");
    const option = select.options[select.selectedIndex];
    const preview = document.getElementById("graduatePreview");
    if (!option || !option.value) {
      preview.hidden = true;
      return;
    }
    document.getElementById("previewCode").textContent = option.dataset.code || "—";
    document.getElementById("previewName").textContent = option.dataset.name || "—";
    document.getElementById("previewJob").textContent = option.dataset.job || "—";
    preview.hidden = false;
  }

  function updateReview() {
    const select = document.getElementById("graduateSelect");
    const option = select.options[select.selectedIndex];
    const summary = option && option.value ? "บัณฑิตที่ประเมิน: " + option.textContent : "ยังไม่ได้เลือกบัณฑิต";
    document.getElementById("reviewGraduate").textContent = summary;
    const finalSummary = document.getElementById("reviewGraduateStep5");
    if (finalSummary) finalSummary.textContent = summary;
  }

  next.addEventListener("click", () => {
    if (validateCurrentStep()) showStep(Math.min(current + 1, steps.length - 1));
  });
  previous.addEventListener("click", () => showStep(Math.max(current - 1, 0)));
  document.getElementById("graduateSelect").addEventListener("change", updateGraduatePreview);
  showStep(0);
})();
