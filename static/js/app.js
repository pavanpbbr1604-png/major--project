document.addEventListener("DOMContentLoaded", () => {
    // Navigation & Tab Switching
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            navButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(pane => pane.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");

            if (targetTab === "tab-history") {
                loadHistoryTable();
            }
        });
    });

    // Upload Mode Selection Handler
    const perspectiveSelect = document.getElementById("perspective-select");
    const lblOverlap = document.getElementById("lbl-overlap-factor");
    const sliderOverlap = document.getElementById("param-overlap-factor");
    const valOverlap = document.getElementById("val-overlap-factor");

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

    // Populate SQL Logs Analysis History
    function loadHistoryTable() {
        const tbody = document.getElementById("history-table-body");
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center">Fetching sqlite history logs...</td></tr>';

        fetch("/history")
        .then(response => response.json())
        .then(data => {
            tbody.innerHTML = "";
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center">No analysis runs stored in DB yet.</td></tr>';
                return;
            }

            data.forEach(row => {
                const tr = document.createElement("tr");
                const timeString = new Date(row.timestamp).toLocaleString();
                const imageCount = row.uploaded_image_names.length;
                
                tr.innerHTML = `
                    <td style="font-family:monospace; font-size:11px">${row.analysis_id.substring(0,8)}...</td>
                    <td>${timeString}</td>
                    <td>${row.uploaded_image_names.join(", ")} (${imageCount} view${imageCount > 1 ? 's' : ''})</td>
                    <td style="font-weight:600">${row.count}</td>
                    <td>${row.density.toFixed(2)}%</td>
                    <td><span class="badge ${row.crowd_level === 'Undercrowded' ? 'badge-success' : row.crowd_level === 'Moderate' ? 'badge-warning' : 'badge-danger'}">${row.crowd_level}</span></td>
                    <td>${(row.reliability_score * 100).toFixed(0)}%</td>
                    <td><button class="view-record-btn" data-id="${row.analysis_id}">View</button></td>
                `;
                
                tbody.appendChild(tr);
            });

            // Add click handlers for row views
            document.querySelectorAll(".view-record-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const id = btn.getAttribute("data-id");
                    loadHistoricRecord(id, data);
                });
            });
        })
        .catch(err => {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--status-danger)">History Fetch Failed: ${err.message}</td></tr>`;
        });
    }

    document.getElementById("btn-refresh-history").addEventListener("click", () => {
        loadHistoryTable();
    });

    // Load Historic Run details back to Upload Panel tab
    function loadHistoricRecord(analysisId, rawData) {
        const record = rawData.find(r => r.analysis_id === analysisId);
        if (!record) return;

        // Switch to upload tab
        navButtons[0].click();

        // Render mock historic representation structure
        const resultsDisplay = document.getElementById("results-display");
        resultsDisplay.classList.remove("hidden");

        document.getElementById("res-count").textContent = record.count;
        document.getElementById("res-density").textContent = `${record.density.toFixed(2)}%`;
        document.getElementById("res-level").textContent = record.crowd_level;
        document.getElementById("res-reliability-score").textContent = `${(record.reliability_score * 100).toFixed(0)}%`;

        const relText = record.fusion_count ? "Consensus" : "Exact/Fallback Match";
        const reliabilityBadge = document.getElementById("badge-reliability");
        reliabilityBadge.textContent = relText;
        reliabilityBadge.className = "badge badge-neutral";

        drawDensityGauge(record.density);

        // Hide multi detail view card if it was single, show if multi
        const detailsCard = document.getElementById("fusion-breakdown-card");
        if (record.fusion_count && record.per_image_details && record.per_image_details.fusion) {
            detailsCard.classList.remove("hidden");
            const container = document.getElementById("fusion-views-container");
            container.innerHTML = "";
            
            record.per_image_details.views.forEach((view, index) => {
                const viewCard = document.createElement("div");
                viewCard.className = "fusion-view-card";
                viewCard.innerHTML = `
                    <span class="fusion-view-title">${view.filename || `View ${index+1}`}</span>
                    <div class="fusion-view-value">${view.counting.total_count} People</div>
                    <div style="font-size:11px;color:var(--text-muted)">Density: ${view.density.density_percentage.toFixed(1)}%</div>
                `;
                container.appendChild(viewCard);
            });
            document.getElementById("fusion-strategy-text").textContent = record.per_image_details.fusion.fusion_strategy;
        } else {
            detailsCard.classList.add("hidden");
        }

        // Reset image containers to placeholders during historical views
        document.getElementById("img-original").src = "";
        document.getElementById("img-processed").src = "";
        document.getElementById("view-tab-row").classList.add("hidden");
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

    // 5. Scroll Parallax for Hero Section
    const heroSection = document.querySelector(".hero-section");
    const dashboardContainer = document.querySelector(".centered-dashboard-container");

    if (heroSection && dashboardContainer) {
        // Ensure dashboard sits on top of the hero section
        dashboardContainer.style.zIndex = "10";
        heroSection.style.zIndex = "1";
        heroSection.style.position = "relative";
        heroSection.style.transformOrigin = "center top"; // Scale from the top

        window.addEventListener("scroll", () => {
            if (document.getElementById("tab-upload").classList.contains("active")) {
                const scrollY = window.scrollY;
                
                // Fade out extremely fast (completely vanished by 120px)
                let opacity = 1 - (scrollY / 120);
                opacity = Math.max(0, opacity);
                
                // Shrink rapidly into the screen
                let scale = 1 - (scrollY / 400);
                scale = Math.max(0.5, scale);
                
                // Translate downwards (parallax)
                let translateY = scrollY * 0.4;
                
                heroSection.style.opacity = opacity;
                
                // If completely faded out, hide it from pointer events just in case
                if (opacity === 0) {
                    heroSection.style.pointerEvents = "none";
                } else {
                    heroSection.style.pointerEvents = "auto";
                }
                
                heroSection.style.transform = `translateY(${translateY}px) scale(${scale})`;
            }
        }, { passive: true });
    }
});
