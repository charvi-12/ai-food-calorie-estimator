(() => {
  const input = document.getElementById("image-input");
  const zone = document.getElementById("upload-zone");
  const preview = document.getElementById("image-preview");
  const previewImage = document.getElementById("preview-image");
  const previewName = document.getElementById("preview-name");
  const removeButton = document.getElementById("remove-image");

  if (input && zone && preview && previewImage && previewName && removeButton) {
    let previewUrl = "";
    const displayPreview = (file) => {
      if (!file) return;
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = URL.createObjectURL(file);
      previewImage.src = previewUrl;
      previewName.textContent = file.name;
      preview.hidden = false;
      zone.classList.add("upload-zone-selected");
      zone.querySelector("#upload-title").textContent = "Choose a different photo";
    };
    input.addEventListener("change", () => displayPreview(input.files[0]));
    removeButton.addEventListener("click", () => {
      input.value = "";
      document.querySelector('input[name="image_filename"]').value = "";
      preview.hidden = true;
      previewImage.removeAttribute("src");
      zone.classList.remove("upload-zone-selected");
      zone.querySelector("#upload-title").innerHTML = 'Drop a photo here, or <span>browse</span>';
    });
    const initialImage = preview.dataset.imageUrl;
    if (initialImage) {
      previewImage.src = initialImage;
      previewName.textContent = "Uploaded food photo";
      preview.hidden = false;
      zone.classList.add("upload-zone-selected");
      zone.querySelector("#upload-title").textContent = "Choose a different photo";
    }
    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      zone.classList.add("upload-zone-dragging");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("upload-zone-dragging"));
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      zone.classList.remove("upload-zone-dragging");
      const [file] = event.dataTransfer.files;
      if (!file) return;
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      displayPreview(file);
    });
  }

  const chartData = document.getElementById("weekly-data");
  const canvas = document.getElementById("calorie-chart");
  if (chartData && canvas && window.Chart) {
    const data = JSON.parse(chartData.textContent);
    const context = canvas.getContext("2d");
    new Chart(context, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [{
          data: data.calories,
          backgroundColor: data.dates.map((day) => day === data.today ? "#486b53" : "#dce8dc"),
          hoverBackgroundColor: "#486b53",
          borderRadius: 7,
          borderSkipped: false,
          maxBarThickness: 32,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#263c2c",
            padding: 12,
            displayColors: false,
            callbacks: { label: (context) => `${context.parsed.y} estimated kcal` },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: { color: "#939a91", font: { family: "DM Sans", size: 11 } },
          },
          y: {
            beginAtZero: true,
            border: { display: false, dash: [4, 4] },
            grid: { color: "#eff1ea", drawTicks: false },
            ticks: { color: "#a2a69f", padding: 12, font: { family: "DM Sans", size: 10 }, maxTicksLimit: 5 },
          },
        },
      },
    });
  }

  const dateInput = document.getElementById("history-date");
  if (dateInput) dateInput.max = new Date().toISOString().slice(0, 10);
})();
