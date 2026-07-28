document.addEventListener("DOMContentLoaded", () => {
    // Navigation & Tab Switching
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    function exitHistoryMode() {
        sessionStorage.removeItem("activeHistoryRecord");
        const uploadPanelCard = document.getElementById("upload-panel-card");
        if (uploadPanelCard) uploadPanelCard.classList.remove("hidden");
        const hero = document.getElementById("hero-section");
        if (hero) hero.classList.remove("hidden");
        const banner = document.getElementById("history-view-banner");
        if (banner) banner.classList.add("hidden");
    }

    const exitHistoryBtn = document.getElementById("btn-exit-history-mode");
    if (exitHistoryBtn) {
        exitHistoryBtn.addEventListener("click", () => {
            exitHistoryMode();
            const uploadPanelCard = document.getElementById("upload-panel-card");
            if (uploadPanelCard) uploadPanelCard.scrollIntoView({ behavior: "smooth" });
        });
    }

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            navButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(pane => pane.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");

            if (targetTab === "tab-upload") {
                exitHistoryMode();
            } else if (targetTab === "tab-history") {
                loadHistoryTable();
            }
        });
    });

    // Upload Mode Selection Handler
    const perspectiveSelect = document.getElementById("perspective-select");
    const lblOverlap = document.getElementById("lbl-overlap-factor");
    const sliderOverlap = document.getElementById("param-overlap-factor");
    const valOverlap = document.getElementById("val-overlap-factor");
    const sliderConf = document.getElementById("param-conf-threshold");
    const valConf = document.getElementById("val-conf-threshold");
    const sliderIoU = document.getElementById("param-iou-threshold");
    const valIoU = document.getElementById("val-iou-threshold");

    let isMultiMode = false;
    let selectedPerspectives = 1;

    perspectiveSelect.addEventListener("change", (e) => {
        selectedPerspectives = parseInt(e.target.value, 10);
        isMultiMode = (selectedPerspectives > 1);

        // Show/hide perspective overlap factor settings
        if (isMultiMode) {
            lblOverlap.classList.remove("hidden");
            sliderOverlap.classList.remove("hidden");
            valOverlap.classList.remove("hidden");
        } else {
            lblOverlap.classList.add("hidden");
            sliderOverlap.classList.add("hidden");
            valOverlap.classList.add("hidden");
        }

        // Show/hide dropzones based on selected number of perspectives
        for (let i = 1; i <= 4; i++) {
            const item = document.getElementById(`item-view${i}`);
            if (i <= selectedPerspectives) {
                item.classList.remove("hidden");
            } else {
                item.classList.add("hidden");
                // Clear any stored file for hidden perspective
                clearFileInput(`input-view${i}`, `preview-view${i}`, `wrapper-view${i}`, `label-view${i}`, `view${i}`);
            }
        }

        checkFormValidity();
    });

    // Hidden overlap controls by default for single mode
    lblOverlap.classList.add("hidden");
    sliderOverlap.classList.add("hidden");
    valOverlap.classList.add("hidden");

    sliderOverlap.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value).toFixed(2);
        let overlapDesc = "Moderate Overlap";
        if (val < 0.2) overlapDesc = "Disjoint Views";
        else if (val < 0.4) overlapDesc = "Low Overlap";
        else if (val > 0.7) overlapDesc = "High Overlap / Identical";
        
        valOverlap.textContent = `${val} (${overlapDesc})`;
    });

    sliderConf.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value).toFixed(2);
        let confDesc = "Standard";
        if (val < 0.15) confDesc = "High Sensitivity (Noise)";
        else if (val < 0.25) confDesc = "Medium-High";
        else if (val > 0.50) confDesc = "Strict / Clean";
        
        valConf.textContent = `${val} (${confDesc})`;
    });

    sliderIoU.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value).toFixed(2);
        let iouDesc = "Standard";
        if (val < 0.35) iouDesc = "Strict (Suppress overlap)";
        else if (val < 0.55) iouDesc = "Balanced / Standard";
        else if (val > 0.70) iouDesc = "Loose (Keep dense overlapping)";
        
        valIoU.textContent = `${val} (${iouDesc})`;
    });

    // Form inputs change handler for tiled inference
    const paramTiled = document.getElementById("param-tiled");
    const tilingParamsDiv = document.getElementById("tiling-params");
    paramTiled.addEventListener("change", () => {
        if (paramTiled.checked) {
            tilingParamsDiv.classList.remove("hidden");
        } else {
            tilingParamsDiv.classList.add("hidden");
        }
    });

    // Files Storage & Dropzone Previews
    const filesStore = {
        view1: null,
        view2: null,
        view3: null,
        view4: null
    };

    function clearFileInput(inputElementId, previewImgId, wrapperDivId, labelId, storeKey) {
        const input = document.getElementById(inputElementId);
        if (input) input.value = "";
        
        const preview = document.getElementById(previewImgId);
        if (preview) preview.src = "";
        
        const wrapper = document.getElementById(wrapperDivId);
        if (wrapper) wrapper.classList.add("hidden");
        
        const label = document.getElementById(labelId);
        if (label) label.classList.remove("hidden");
        
        filesStore[storeKey] = null;
    }

    function setupFileInput(inputElementId, previewImgId, wrapperDivId, removeBtnId, storeKey) {
        const input = document.getElementById(inputElementId);
        const preview = document.getElementById(previewImgId);
        const wrapper = document.getElementById(wrapperDivId);
        const label = input.parentElement;
        const removeBtn = document.getElementById(removeBtnId);

        // File Selection via Input
        input.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    preview.src = event.target.result;
                    filesStore[storeKey] = file;
                    label.classList.add("hidden");
                    wrapper.classList.remove("hidden");
                    checkFormValidity();
                };
                reader.readAsDataURL(file);
            }
        });

        // Drag & Drop Functionality
        label.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.stopPropagation();
            label.classList.add("dragover");
        });

        label.addEventListener("dragleave", (e) => {
            e.preventDefault();
            e.stopPropagation();
            label.classList.remove("dragover");
        });

        label.addEventListener("drop", (e) => {
            e.preventDefault();
            e.stopPropagation();
            label.classList.remove("dragover");
            
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith("image/")) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    preview.src = event.target.result;
                    filesStore[storeKey] = file;
                    label.classList.add("hidden");
                    wrapper.classList.remove("hidden");
                    checkFormValidity();
                };
                reader.readAsDataURL(file);
            }
        });

        removeBtn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            input.value = "";
            preview.src = "";
            filesStore[storeKey] = null;
            wrapper.classList.add("hidden");
            label.classList.remove("hidden");
            checkFormValidity();
        });
    }

    setupFileInput("input-view1", "preview-view1", "wrapper-view1", "remove-view1", "view1");
    setupFileInput("input-view2", "preview-view2", "wrapper-view2", "remove-view2", "view2");
    setupFileInput("input-view3", "preview-view3", "wrapper-view3", "remove-view3", "view3");
    setupFileInput("input-view4", "preview-view4", "wrapper-view4", "remove-view4", "view4");
    // Reset Iteration Button
    const btnResetIteration = document.getElementById("btn-reset-iteration");
    if (btnResetIteration) {
        btnResetIteration.addEventListener("click", () => {
            sessionStorage.removeItem("lastAnalysisData");
            sessionStorage.removeItem("lastIsMultiMode");
            // Clear all file inputs by triggering the remove buttons
            for (let i = 1; i <= 4; i++) {
                const removeBtn = document.getElementById(`remove-view${i}`);
                if (removeBtn) {
                    removeBtn.click();
                }
            }
            // Hide the results dashboard
            const resultsDisplay = document.getElementById("results-display");
            if (resultsDisplay) {
                resultsDisplay.classList.add("hidden");
            }
            // Hide the reset button itself
            btnResetIteration.classList.add("hidden");
            // Scroll smoothly to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Enable/Disable Analyze Button based on selection status
    const btnAnalyze = document.getElementById("btn-analyze");

    function checkFormValidity() {
        // All active views must be populated
        let valid = true;
        for (let i = 1; i <= selectedPerspectives; i++) {
            if (filesStore[`view${i}`] === null) {
                valid = false;
                break;
            }
        }
        btnAnalyze.disabled = !valid;
    }

    // Submit Form
    btnAnalyze.addEventListener("click", () => {
        executeAnalysis();
    });

    function executeAnalysis() {
        const loadingSpinner = document.getElementById("loading-spinner");
        loadingSpinner.classList.remove("hidden");

        const formData = new FormData();
        const urlParams = new URLSearchParams();

        // Standard inputs
        urlParams.append("imgsz", document.getElementById("param-imgsz").value);
        urlParams.append("tiled", paramTiled.checked.toString());
        urlParams.append("tile_size", document.getElementById("param-tile-size").value);
        urlParams.append("tile_overlap", document.getElementById("param-tile-overlap").value);
        urlParams.append("tta", document.getElementById("param-tta").checked.toString());
        urlParams.append("conf_threshold", document.getElementById("param-conf-threshold").value);
        urlParams.append("iou_threshold", document.getElementById("param-iou-threshold").value);
        urlParams.append("deep_search", document.getElementById("param-deep-search").checked.toString());
        urlParams.append("sharpen", document.getElementById("param-sharpen").checked.toString());

        let targetUrl = "/analyze";

        if (!isMultiMode) {
            targetUrl = "/analyze";
            formData.append("image", filesStore.view1);
        } else {
            targetUrl = "/analyze_multi";
            urlParams.append("overlap_factor", sliderOverlap.value);
            
            for (let i = 1; i <= selectedPerspectives; i++) {
                if (filesStore[`view${i}`]) {
                    formData.append(`image${i}`, filesStore[`view${i}`]);
                }
            }
        }

        const requestUrl = `${targetUrl}?${urlParams.toString()}`;

        fetch(requestUrl, {
            method: "POST",
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Pipeline computation error");
            }
            return response.json();
        })
        .then(data => {
            sessionStorage.setItem("lastAnalysisData", JSON.stringify(data));
            sessionStorage.setItem("lastIsMultiMode", JSON.stringify(isMultiMode));
            renderResults(data, isMultiMode);
        })
        .catch(err => {
            alert(`Analysis Failed: ${err.message}`);
        })
        .finally(() => {
            loadingSpinner.classList.add("hidden");
        });
    }

    // Render Metrics Results
    function renderResults(data, isMulti) {
        const resultsDisplay = document.getElementById("results-display");
        resultsDisplay.classList.remove("hidden");

        if (data && data.analysis_id) {
            activeAnalysisId = data.analysis_id;
        }
        
        // Show the reset iteration button
        const btnResetIteration = document.getElementById("btn-reset-iteration");
        if (btnResetIteration) {
            btnResetIteration.classList.remove("hidden");
        }

        // Primary statistics
        const count = isMulti ? data.fusion.unified_count : data.counting.total_count;
        const densityPct = isMulti ? data.average_density_percentage : data.density.density_percentage;
        const level = data.classification.crowd_level;
        const relScore = isMulti ? data.fusion.fusion_confidence_score : data.reliability.reliability_score;
        const relText = isMulti ? "Consensus" : data.reliability.formatted_count;
        
        // 1. Text elements
        document.getElementById("res-count").textContent = count;
        document.getElementById("res-density").textContent = `${densityPct.toFixed(2)}%`;
        document.getElementById("res-level").textContent = level;
        document.getElementById("res-reliability-score").textContent = `${(relScore * 100).toFixed(0)}%`;

        // 2. Badge Color Coding
        const reliabilityBadge = document.getElementById("badge-reliability");
        reliabilityBadge.textContent = relText;
        reliabilityBadge.className = "badge"; // Reset classes
        
        if (isMulti) {
            reliabilityBadge.classList.add("badge-success");
        } else {
            if (data.reliability.is_reliable) {
                reliabilityBadge.classList.add("badge-success");
            } else {
                reliabilityBadge.classList.add("badge-warning");
            }
        }

        // Color coding for Crowd Level status
        const levelText = document.getElementById("res-level");
        if (level === "Undercrowded") {
            levelText.style.color = "var(--status-success)";
        } else if (level === "Moderate") {
            levelText.style.color = "var(--status-warning)";
        } else {
            levelText.style.color = "var(--status-danger)";
        }

        // 3. Draw Progress Ring Gauge
        drawDensityGauge(densityPct);

        // 4. Details panel
        if (!isMulti) {
            const singleView = data;
            document.getElementById("val-avg-conf").textContent = `${(singleView.reliability.average_confidence * 100).toFixed(1)}%`;
            document.getElementById("val-small-ratio").textContent = `${(singleView.reliability.small_object_ratio * 100).toFixed(1)}%`;
            document.getElementById("val-occlusion").textContent = `${(singleView.reliability.occlusion_ratio * 100).toFixed(1)}%`;
            document.getElementById("val-consistency").textContent = `${(singleView.reliability.consistency_score * 100).toFixed(1)}%`;
            
            const explanation = singleView.reliability.is_reliable 
                ? "Optimal Detection Environment. High certainty, outputting exact counts."
                : "High Occlusion or Tiny Objects detected. Fallback estimate used.";
            document.getElementById("res-explanation").textContent = explanation;
            
            document.getElementById("fusion-breakdown-card").classList.add("hidden");
            
            // Set single visual comparison images
            setComparisonImages(singleView, isMulti);
        } else {
            document.getElementById("val-avg-conf").textContent = "-";
            document.getElementById("val-small-ratio").textContent = "-";
            document.getElementById("val-occlusion").textContent = "-";
            document.getElementById("val-consistency").textContent = "-";
            document.getElementById("res-explanation").textContent = "Fused Consensus details mapped below.";

            // Render multi perspective breakdowns
            const breakdownCard = document.getElementById("fusion-breakdown-card");
            breakdownCard.classList.remove("hidden");

            const container = document.getElementById("fusion-views-container");
            container.innerHTML = ""; // Clear
            
            data.views.forEach((view, index) => {
                const viewCard = document.createElement("div");
                viewCard.className = "fusion-view-card";
                viewCard.innerHTML = `
                    <span class="fusion-view-title">${view.filename || `View ${index+1}`}</span>
                    <div class="fusion-view-value">${view.counting.total_count} People</div>
                    <div style="font-size:11px;color:var(--text-muted)">Density: ${view.density.density_percentage.toFixed(1)}%</div>
                `;
                container.appendChild(viewCard);
            });

            document.getElementById("fusion-strategy-text").textContent = data.fusion.fusion_strategy;

            // Image comparisons selector for multiple perspectives
            setComparisonImages(data.views, isMulti);
        }

        // Scroll to results
        resultsDisplay.scrollIntoView({ behavior: 'smooth' });
    }

    // Draw Circular Gauge
    function drawDensityGauge(percent) {
        const canvas = document.getElementById("gauge-canvas");
        const ctx = canvas.getContext("2d");
        const x = canvas.width / 2;
        const y = canvas.height / 2;
        const radius = 80;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw track ring
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
        ctx.lineWidth = 14;
        ctx.stroke();

        // Draw progress arc
        const endAngle = (percent / 100) * 2 * Math.PI - 0.5 * Math.PI;
        ctx.beginPath();
        ctx.arc(x, y, radius, -0.5 * Math.PI, endAngle);
        
        // Select color gradient based on density
        let ringColor = "var(--primary-color)";
        if (percent >= 45.0) ringColor = "var(--status-danger)";
        else if (percent >= 15.0) ringColor = "var(--status-warning)";
        else ringColor = "var(--status-success)";

        ctx.strokeStyle = ringColor;
        ctx.lineWidth = 14;
        ctx.lineCap = "round";
        ctx.stroke();

        document.getElementById("gauge-text").textContent = `${percent.toFixed(1)}%`;
    }

    // Multi-perspective image tabs selector setup
    function setComparisonImages(viewData, isMulti) {
        const tabRow = document.getElementById("view-tab-row");
        const imgOrig = document.getElementById("img-original");
        const imgProc = document.getElementById("img-processed");

        if (!isMulti) {
            tabRow.classList.add("hidden");
            if (viewData && viewData.original_url && viewData.processed_url) {
                imgOrig.src = viewData.original_url;
                imgProc.src = viewData.processed_url;
            } else {
                const fileObj = filesStore.single;
                if (fileObj) {
                    const url = URL.createObjectURL(fileObj);
                    imgOrig.src = url;
                    imgProc.src = url;
                }
            }
        } else {
            tabRow.classList.remove("hidden");
            tabRow.innerHTML = "";

            viewData.forEach((view, idx) => {
                const btn = document.createElement("button");
                btn.className = `view-select-btn ${idx === 0 ? 'active' : ''}`;
                btn.textContent = view.filename || `Perspective ${idx + 1}`;
                btn.addEventListener("click", () => {
                    document.querySelectorAll(".view-select-btn").forEach(b => b.classList.remove("active"));
                    btn.classList.add("active");
                    loadPerspectiveImages(view, idx);
                });
                tabRow.appendChild(btn);
            });

            // Load first perspective by default
            loadPerspectiveImages(viewData[0], 0);
        }
    }

    function loadPerspectiveImages(view, index) {
        const imgOrig = document.getElementById("img-original");
        const imgProc = document.getElementById("img-processed");
        
        if (view && view.original_url && view.processed_url) {
            imgOrig.src = view.original_url;
            imgProc.src = view.processed_url;
        } else {
            const storeKeys = ["view1", "view2", "view3", "view4"];
            const fileObj = filesStore[storeKeys[index]];
            
            if (fileObj) {
                const url = URL.createObjectURL(fileObj);
                imgOrig.src = url;
                imgProc.src = url;
            }
        }
    }

    // Modal Image Viewer Zoom Layout
    const modal = document.getElementById("image-modal");
    const modalImg = document.getElementById("modal-img-element");
    const modalClose = document.getElementById("modal-close-btn");

    function setupZoom(imgElementId) {
        const img = document.getElementById(imgElementId);
        img.parentElement.addEventListener("click", () => {
            if (img.src) {
                modal.classList.remove("hidden");
                modalImg.src = img.src;
            }
        });
    }

    setupZoom("img-original");
    setupZoom("img-processed");

    modalClose.addEventListener("click", () => {
        modal.classList.add("hidden");
    });
    
    modal.addEventListener("click", (e) => {
        if (e.target === modal) {
            modal.classList.add("hidden");
        }
    });

    function resolveImageUrl(rawUrl, analysisId, isProcessed = true, viewIdx = 1) {
        if (rawUrl && typeof rawUrl === "string" && rawUrl.trim() !== "") {
            let clean = rawUrl.trim();
            return clean.startsWith("/") ? clean : "/" + clean;
        }
        const suffix = isProcessed ? "processed.jpg" : "original.jpg";
        if (viewIdx > 1) {
            return `/static/uploads/${analysisId}_view${viewIdx}_${suffix}`;
        }
        return `/static/uploads/${analysisId}_${suffix}`;
    }

    function setSafeImage(imgElementId, url, fallbackText = "Image Not Available") {
        const img = document.getElementById(imgElementId);
        if (!img) return;
        
        const svgPlaceholder = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='600' height='400' viewBox='0 0 600 400'%3E%3Crect width='600' height='400' fill='%230f172a' rx='12'/%3E%3Cpath d='M250 180 L280 220 L310 190 L350 240 L230 240 Z' fill='%23334155'/%3E%3Ccircle cx='320' cy='160' r='18' fill='%23475569'/%3E%3Ctext x='50%25' y='75%25' dominant-baseline='middle' text-anchor='middle' fill='%2394a3b8' font-family='sans-serif' font-size='15' font-weight='600'%3E" + encodeURIComponent(fallbackText) + "%3C/text%3E%3C/svg%3E";

        if (!url || url.trim() === "") {
            img.src = svgPlaceholder;
            return;
        }

        img.onerror = () => {
            img.onerror = null;
            img.src = svgPlaceholder;
        };

        img.src = url;
    }

    let timeseriesChartInstance = null;
    let distributionChartInstance = null;
    let activeAnalysisId = null;

    function renderAnalyticsCharts(historyData) {
        if (!window.Chart || !historyData || historyData.length === 0) return;

        // Sort data chronologically (oldest to newest for timeseries)
        const sortedData = [...historyData].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        const labels = sortedData.map(r => {
            const dt = new Date(r.timestamp);
            return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });

        const counts = sortedData.map(r => r.count || 0);

        // 1. Render Time-Series Headcount Line Chart
        const tsCtx = document.getElementById("chart-timeseries");
        if (tsCtx) {
            if (timeseriesChartInstance) {
                timeseriesChartInstance.destroy();
            }
            timeseriesChartInstance = new Chart(tsCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Estimated Crowd Count',
                        data: counts,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#0f172a',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(15, 23, 42, 0.06)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        // 2. Render Congestion Risk Level Distribution Donut Chart
        let underCount = 0, modCount = 0, overCount = 0;
        historyData.forEach(r => {
            const lvl = r.crowd_level || "Moderate";
            if (lvl === "Undercrowded") underCount++;
            else if (lvl === "Moderate") modCount++;
            else if (lvl === "Overcrowded") overCount++;
        });

        const distCtx = document.getElementById("chart-distribution");
        if (distCtx) {
            if (distributionChartInstance) {
                distributionChartInstance.destroy();
            }
            distributionChartInstance = new Chart(distCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Undercrowded', 'Moderate', 'Overcrowded'],
                    datasets: [{
                        data: [underCount, modCount, overCount],
                        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { font: { family: 'Inter', size: 11 }, usePointStyle: true }
                        }
                    }
                }
            });
        }
    }

    // Populate SQL Logs Analysis History
    function loadHistoryTable() {
        const tbody = document.getElementById("history-table-body");
        tbody.innerHTML = '<tr><td colspan="11" style="text-align:center">Fetching sqlite history logs...</td></tr>';

        fetch("/history")
        .then(response => response.json())
        .then(data => {
            const historyData = data.data || data; // handle wrapped response
            tbody.innerHTML = "";
            if (!historyData || historyData.length === 0) {
                tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding: 30px; font-weight: bold; color: var(--text-muted)">No analysis runs stored in DB yet.</td></tr>';
                return;
            }

            historyData.forEach((row, index) => {
                const tr = document.createElement("tr");
                const timeString = new Date(row.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
                const imageCount = row.uploaded_image_names ? row.uploaded_image_names.length : 1;
                const sno = index + 1;
                
                // Extract processed image thumbnail URL from per_image_details
                let thumbUrl = "";
                if (row.per_image_details && row.per_image_details.views && row.per_image_details.views.length > 0) {
                    thumbUrl = resolveImageUrl(row.per_image_details.views[0].processed_url || row.per_image_details.views[0].original_url, row.analysis_id, true, 1);
                } else {
                    thumbUrl = resolveImageUrl(null, row.analysis_id, true, 1);
                }
                
                const thumbHtml = `<img src="${thumbUrl}" class="history-thumb-img" title="Click to zoom annotated processed image with detections" data-url="${thumbUrl}" style="margin:0 auto;" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'100\' height=\'70\' viewBox=\'0 0 100 70\'%3E%3Crect width=\'100\' height=\'70\' fill=\'%230f172a\'/%3E%3Ctext x=\'50%25\' y=\'50%25\' dominant-baseline=\'middle\' text-anchor=\'middle\' fill=\'%2394a3b8\' font-size=\'10\'%3EN/A%3C/text%3E%3C/svg%3E'">`;

                const rawImgNames = row.uploaded_image_names ? row.uploaded_image_names.join(", ") : 'Image';
                const imgDisplayHtml = `<div style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:500;" title="${rawImgNames}">${rawImgNames}</div><span style="font-size:10px; color:var(--text-muted);">(${imageCount} view${imageCount > 1 ? 's' : ''})</span>`;

                tr.innerHTML = `
                    <td style="font-weight:700; color:var(--text-main); text-align:center;">#${sno}</td>
                    <td style="font-size:11px; white-space:nowrap;">${timeString}</td>
                    <td style="text-align:center;">${thumbHtml}</td>
                    <td>${imgDisplayHtml}</td>
                    <td style="font-weight:700; text-align:center;">${row.count}</td>
                    <td style="text-align:center;">${row.density ? row.density.toFixed(1) : 0}%</td>
                    <td style="text-align:center;"><span class="badge ${row.crowd_level === 'Undercrowded' ? 'badge-success' : row.crowd_level === 'Moderate' ? 'badge-warning' : 'badge-danger'}" style="font-size:10px; padding:3px 6px;">${row.crowd_level}</span></td>
                    <td style="text-align:center; font-weight:600;">${(row.reliability_score * 100).toFixed(0)}%</td>
                    <td style="text-align:center;"><button class="pdf-record-btn btn-mini" data-id="${row.analysis_id}" style="background:#0f172a; color:white; border:none; padding:4px 6px; border-radius:5px; font-weight:700; font-size:10px; cursor:pointer;" title="Download PDF Executive Report">📄 PDF</button></td>
                    <td style="text-align:center;"><button class="view-record-btn" data-id="${row.analysis_id}" data-sno="${sno}" style="padding:4px 8px; font-size:10px;">View</button></td>
                    <td style="text-align:center;"><button class="delete-record-btn" data-id="${row.analysis_id}" title="Delete Record" style="padding:3px; font-size:11px;">🗑️</button></td>
                `;
                
                tbody.appendChild(tr);
            });

            // Render interactive time-series and congestion distribution charts
            renderAnalyticsCharts(historyData);

            // Add click handlers for history image thumbnail preview modal
            document.querySelectorAll(".history-thumb-img").forEach(img => {
                img.addEventListener("click", () => {
                    const url = img.getAttribute("data-url");
                    if (url) {
                        modal.classList.remove("hidden");
                        modalImg.src = url;
                    }
                });
            });

            // Add click handlers for PDF report download
            document.querySelectorAll(".pdf-record-btn").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const id = btn.getAttribute("data-id");
                    window.location.href = `/history/export/pdf/${id}`;
                });
            });

            // Add click handlers for row views
            document.querySelectorAll(".view-record-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const id = btn.getAttribute("data-id");
                    const sno = btn.getAttribute("data-sno");
                    loadHistoricRecord(id, historyData, sno);
                });
            });

            // Add click handlers for row deletes
            document.querySelectorAll(".delete-record-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const id = btn.getAttribute("data-id");
                    showDeleteModal(id);
                });
            });
        })
        .catch(err => {
            tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; color:var(--status-danger)">History Fetch Failed: ${err.message}</td></tr>`;
        });
    }

    // Export CSV Listener
    const exportCsvBtn = document.getElementById("btn-export-csv");
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener("click", () => {
            window.location.href = "/history/export/csv";
        });
    }

    // Download PDF Executive Report Listener (Dashboard Header Button)
    const downloadPdfBtn = document.getElementById("btn-download-pdf-report");
    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener("click", () => {
            let targetId = activeAnalysisId;
            const activeHist = sessionStorage.getItem("activeHistoryRecord");
            if (activeHist) {
                try {
                    const parsed = JSON.parse(activeHist);
                    if (parsed.analysisId) targetId = parsed.analysisId;
                } catch (e) {}
            }
            if (targetId) {
                window.location.href = `/history/export/pdf/${targetId}`;
            } else {
                alert("Please complete an image analysis or select a history record first to download its PDF report.");
            }
        });
    }

    document.getElementById("btn-refresh-history").addEventListener("click", () => {
        loadHistoryTable();
    });

    // Delete History Modal Logic
    let currentDeleteId = null;
    const deleteModal = document.getElementById("delete-confirm-modal");
    
    document.getElementById("btn-clear-history").addEventListener("click", () => {
        const hasRecords = document.querySelectorAll(".delete-record-btn").length > 0;
        if (!hasRecords) {
            document.getElementById("empty-history-modal").classList.remove("hidden");
        } else {
            showDeleteModal("all");
        }
    });

    document.getElementById("btn-close-empty").addEventListener("click", () => {
        document.getElementById("empty-history-modal").classList.add("hidden");
    });

    function showDeleteModal(id) {
        currentDeleteId = id;
        document.getElementById("delete-confirm-text").textContent = id === "all" 
            ? "Are you absolutely sure you want to completely clear the entire analysis history? This cannot be undone."
            : "Are you sure you want to delete this specific analysis record?";
        deleteModal.classList.remove("hidden");
    }

    document.getElementById("btn-cancel-delete").addEventListener("click", () => {
        deleteModal.classList.add("hidden");
        currentDeleteId = null;
    });

    document.getElementById("btn-confirm-delete").addEventListener("click", () => {
        if (!currentDeleteId) return;
        
        const endpoint = currentDeleteId === "all" ? "/history/all" : `/history/${currentDeleteId}`;
        const btn = document.getElementById("btn-confirm-delete");
        btn.disabled = true;
        btn.textContent = "Deleting...";
        
        fetch(endpoint, { method: "DELETE" })
            .then(res => res.json())
            .then(data => {
                deleteModal.classList.add("hidden");
                loadHistoryTable();
            })
            .catch(err => {
                alert("Error deleting record: " + err.message);
                deleteModal.classList.add("hidden");
            })
            .finally(() => {
                btn.disabled = false;
                btn.textContent = "Yes, Delete";
                currentDeleteId = null;
            });
    });

    // Load Historic Run details back to Upload Panel tab
    function loadHistoricRecord(analysisId, rawData, sno = null) {
        const record = rawData.find(r => r.analysis_id === analysisId);
        if (!record) return;

        // Persist history view state so page reload preserves history view mode
        sessionStorage.setItem("activeHistoryRecord", JSON.stringify({ analysisId: analysisId, sno: sno }));

        // Hide upload dropzone card & hero section while viewing history
        const uploadPanelCard = document.getElementById("upload-panel-card");
        if (uploadPanelCard) uploadPanelCard.classList.add("hidden");
        const heroSection = document.getElementById("hero-section");
        if (heroSection) heroSection.classList.add("hidden");

        // Show historical record banner
        const historyBanner = document.getElementById("history-view-banner");
        if (historyBanner) {
            historyBanner.classList.remove("hidden");
            const title = document.getElementById("history-banner-title");
            if (title) title.textContent = `Viewing Historical Record ${sno ? '#' + sno : ''}`;
            const subtitle = document.getElementById("history-banner-subtitle");
            const recTime = new Date(record.timestamp).toLocaleString();
            if (subtitle) subtitle.textContent = `Count: ${record.count} people | Density Level: ${record.crowd_level} | Recorded: ${recTime}`;
        }

        // Switch active tab to tab-upload (dashboard pane)
        navButtons.forEach(b => b.classList.remove("active"));
        tabPanes.forEach(pane => pane.classList.remove("active"));
        navButtons[0].classList.add("active");
        document.getElementById("tab-upload").classList.add("active");

        // Render historic representation structure
        const resultsDisplay = document.getElementById("results-display");
        resultsDisplay.classList.remove("hidden");

        // Scroll smoothly to top of dashboard results
        if (historyBanner) {
            historyBanner.scrollIntoView({ behavior: "smooth" });
        } else {
            resultsDisplay.scrollIntoView({ behavior: "smooth" });
        }

        document.getElementById("res-count").textContent = record.count;
        document.getElementById("res-density").textContent = `${record.density ? record.density.toFixed(2) : 0}%`;
        document.getElementById("res-level").textContent = record.crowd_level;
        document.getElementById("res-reliability-score").textContent = `${(record.reliability_score * 100).toFixed(0)}%`;

        const relText = record.fusion_count ? "Consensus Fusion" : "Direct Analysis";
        const reliabilityBadge = document.getElementById("badge-reliability");
        reliabilityBadge.textContent = relText;
        reliabilityBadge.className = "badge badge-neutral";

        drawDensityGauge(record.density || 0);

        // Restore processed and original images from per_image_details
        const views = record.per_image_details && record.per_image_details.views ? record.per_image_details.views : [];
        const viewTabRow = document.getElementById("view-tab-row");

        if (views.length > 0) {
            const firstOrigUrl = resolveImageUrl(views[0].original_url, record.analysis_id, false, 1);
            const firstProcUrl = resolveImageUrl(views[0].processed_url, record.analysis_id, true, 1);

            setSafeImage("img-original", firstOrigUrl, "Original Image Unavailable");
            setSafeImage("img-processed", firstProcUrl, "Processed Detections Unavailable");

            if (views.length > 1) {
                // Multi-perspective view tab switcher
                viewTabRow.classList.remove("hidden");
                viewTabRow.innerHTML = "";
                views.forEach((v, idx) => {
                    const btn = document.createElement("button");
                    btn.className = `view-select-btn ${idx === 0 ? 'active' : ''}`;
                    btn.textContent = `View ${idx + 1} (${v.counting ? v.counting.total_count : v.count || 0} People)`;
                    btn.addEventListener("click", () => {
                        document.querySelectorAll(".view-select-btn").forEach(b => b.classList.remove("active"));
                        btn.classList.add("active");
                        const origUrl = resolveImageUrl(v.original_url, record.analysis_id, false, idx + 1);
                        const procUrl = resolveImageUrl(v.processed_url, record.analysis_id, true, idx + 1);
                        setSafeImage("img-original", origUrl, `View ${idx + 1} Original Unavailable`);
                        setSafeImage("img-processed", procUrl, `View ${idx + 1} Detections Unavailable`);
                    });
                    viewTabRow.appendChild(btn);
                });
            } else {
                viewTabRow.classList.add("hidden");
            }
        } else {
            // Fallback convention URLs if views array missing
            const origUrl = resolveImageUrl(null, record.analysis_id, false, 1);
            const procUrl = resolveImageUrl(null, record.analysis_id, true, 1);
            setSafeImage("img-original", origUrl, "Original Image File Missing");
            setSafeImage("img-processed", procUrl, "Processed Detections File Missing");
            viewTabRow.classList.add("hidden");
        }

        // Populate System Analysis Insights
        const firstView = views.length > 0 ? views[0] : null;
        const rel = (firstView && firstView.reliability) ? firstView.reliability : {};

        document.getElementById("val-avg-conf").textContent = rel.avg_confidence ? `${(rel.avg_confidence * 100).toFixed(1)}%` : `${(record.reliability_score * 100).toFixed(0)}%`;
        document.getElementById("val-small-ratio").textContent = rel.small_object_ratio !== undefined ? `${(rel.small_object_ratio * 100).toFixed(1)}%` : "N/A";
        document.getElementById("val-occlusion").textContent = rel.occlusion_indicator || (record.fusion_count ? "Multi-View Consensus" : "Standard Density");
        document.getElementById("val-consistency").textContent = rel.consistency_score ? `${(rel.consistency_score * 100).toFixed(0)}%` : `${(record.reliability_score * 100).toFixed(0)}%`;
        
        const explanationBox = document.getElementById("res-explanation");
        if (rel.explanation) {
            explanationBox.textContent = rel.explanation;
        } else {
            explanationBox.textContent = `Historical record saved on ${new Date(record.timestamp).toLocaleString()}. Count: ${record.count} people, Density: ${record.density ? record.density.toFixed(1) : 0}%.`;
        }

        // Render multi detail view breakdown card if available
        const detailsCard = document.getElementById("fusion-breakdown-card");
        if (record.fusion_count && record.per_image_details && record.per_image_details.fusion) {
            detailsCard.classList.remove("hidden");
            const container = document.getElementById("fusion-views-container");
            container.innerHTML = "";
            
            record.per_image_details.views.forEach((view, index) => {
                const viewCard = document.createElement("div");
                viewCard.className = "fusion-view-card";
                const vCount = view.counting ? view.counting.total_count : view.count || 0;
                const vDens = view.density ? (view.density.density_percentage || view.density) : 0;
                viewCard.innerHTML = `
                    <span class="fusion-view-title">${view.filename || `View ${index+1}`}</span>
                    <div class="fusion-view-value">${vCount} People</div>
                    <div style="font-size:11px;color:var(--text-muted)">Density: ${vDens.toFixed ? vDens.toFixed(1) : vDens}%</div>
                `;
                container.appendChild(viewCard);
            });
            document.getElementById("fusion-strategy-text").textContent = record.per_image_details.fusion.fusion_strategy;
        } else {
            detailsCard.classList.add("hidden");
        }
    }

    // Mobile Menu Toggle handler
    const navToggle = document.getElementById("nav-toggle");
    const navMenu = document.getElementById("nav-menu");

    if (navToggle && navMenu) {
        navToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            navToggle.classList.toggle("active");
            navMenu.classList.toggle("show");
        });

        // Close mobile menu when clicking nav links
        const menuButtons = navMenu.querySelectorAll(".nav-btn");
        menuButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                navToggle.classList.remove("active");
                navMenu.classList.remove("show");
            });
        });

        // Close mobile menu when clicking outside
        document.addEventListener("click", (e) => {
            if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
                navToggle.classList.remove("active");
                navMenu.classList.remove("show");
            }
        });
    }

    // === PREMIUM AI DASHBOARD ANIMATIONS ===
    
    // 1. Subtle Parallax Lens Glow relative to Mouse Movement
    const radialGlow = document.getElementById("radial-glow");
    if (radialGlow) {
        document.addEventListener("mousemove", (e) => {
            if (document.hidden) return;
            // Calculate offsets
            const moveX = (e.clientX - window.innerWidth / 2) * 0.04;
            const moveY = (e.clientY - window.innerHeight / 2) * 0.04;
            
            // Apply slight transform translation
            radialGlow.style.transform = `translate3d(calc(-50% + ${moveX}px), calc(-50% + ${moveY}px), 0)`;
        });
    }

    // 4. Scrolled Navbar Blur Enhancement (No overrides, styles handled in style.css)
    const navbar = document.querySelector(".navbar");
    if (navbar) {
        window.addEventListener("scroll", () => {
            // Stylings are handled cleanly in style.css to support neubrutalism
        }, { passive: true });
    }

    // 5. Scroll Parallax for Hero Section (Smooth Lerped Scroll)
    const heroSection = document.querySelector(".hero-section");
    const dashboardContainer = document.querySelector(".centered-dashboard-container");

    if (heroSection && dashboardContainer) {
        // Ensure dashboard sits on top of the hero section
        dashboardContainer.style.zIndex = "10";
        heroSection.style.zIndex = "1";
        heroSection.style.position = "relative";
        heroSection.style.transformOrigin = "center top"; // Scale from the top

        let targetScrollY = window.scrollY;
        let currentScrollY = window.scrollY;
        let ticking = false;

        function updateParallax() {
            // Lerp interpolation: currentScrollY crawls towards targetScrollY (12% speed factor per frame)
            currentScrollY += (targetScrollY - currentScrollY) * 0.12;

            if (document.getElementById("tab-upload").classList.contains("active")) {
                const progress = Math.min(currentScrollY / 150, 1);
                
                // Fade out
                let opacity = 1 - progress;

                // Scale down
                let scale = 1 - progress * 0.3;

                // Translate upwards faster than scroll (so it retreats up and vanishes)
                let translateY = -currentScrollY * 0.8;

                heroSection.style.opacity = opacity;

                if (opacity === 0) {
                    heroSection.style.pointerEvents = "none";
                } else {
                    heroSection.style.pointerEvents = "auto";
                }

                heroSection.style.transform = `translate3d(0, ${translateY}px, 0) scale(${scale})`;
            }

            // Continue loop if not yet fully converged
            if (Math.abs(targetScrollY - currentScrollY) > 0.05) {
                requestAnimationFrame(updateParallax);
            } else {
                currentScrollY = targetScrollY;
                ticking = false;
            }
        }

        window.addEventListener("scroll", () => {
            targetScrollY = window.scrollY;
            if (!ticking) {
                ticking = true;
                requestAnimationFrame(updateParallax);
            }
        }, { passive: true });
    }

    // Restore session data or history view state if page refreshed
    const savedHistoryView = sessionStorage.getItem("activeHistoryRecord");
    if (savedHistoryView) {
        try {
            const histInfo = JSON.parse(savedHistoryView);
            fetch("/history")
                .then(res => res.json())
                .then(data => {
                    const historyData = data.data || data;
                    if (historyData && historyData.length > 0) {
                        loadHistoricRecord(histInfo.analysisId, historyData, histInfo.sno);
                    }
                })
                .catch(err => console.error("Failed to restore history view on reload", err));
        } catch (e) {
            console.error("Error parsing savedHistoryView", e);
        }
    } else {
        const lastData = sessionStorage.getItem("lastAnalysisData");
        if (lastData) {
            try {
                const data = JSON.parse(lastData);
                const isMulti = JSON.parse(sessionStorage.getItem("lastIsMultiMode") || "false");
                
                if (!isMulti) {
                    const preview = document.getElementById("preview-view1");
                    if (preview && data.original_url) {
                        preview.src = data.original_url;
                        document.getElementById("label-view1").classList.add("hidden");
                        document.getElementById("wrapper-view1").classList.remove("hidden");
                    }
                } else {
                    perspectiveSelect.value = data.perspectives.length;
                    perspectiveSelect.dispatchEvent(new Event("change"));
                    for (let i = 0; i < data.perspectives.length; i++) {
                        const preview = document.getElementById(`preview-view${i+1}`);
                        if (preview && data.perspectives[i].original_url) {
                            preview.src = data.perspectives[i].original_url;
                            document.getElementById(`label-view${i+1}`).classList.add("hidden");
                            document.getElementById(`wrapper-view${i+1}`).classList.remove("hidden");
                        }
                    }
                }
                renderResults(data, isMulti);
            } catch (e) {
                console.error("Failed to restore session", e);
            }
        }
    }
});
