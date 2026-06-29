// Open Peeps Crowd Simulator Background Component
document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("crowd-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let peeps = [];
    let animationFrameId = null;
    let isTabActive = true;

    // City Background Elements
    let buildings = [];
    let trafficLight = { x: 0, y: 0 };

    // Sprite sheet configuration
    const img = new Image();
    img.src = "https://s3-us-west-2.amazonaws.com/s.cdpn.io/175711/open-peeps-sheet.png";
    
    const rows = 7;
    const cols = 15;
    let spriteWidth = 0;
    let spriteHeight = 0;
    let isLoaded = false;

    img.onload = () => {
        spriteWidth = img.naturalWidth / cols;
        spriteHeight = img.naturalHeight / rows;
        isLoaded = true;
        
        // Spawn city geometry and initial crowd
        initCityBackground();
        initCrowd();
        animateCrowd();
    };

    // Resize handling
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        // Keep canvas size consistent (height of 400px on screen)
        canvas.height = 400; 
    }
    window.addEventListener("resize", () => {
        resizeCanvas();
        if (isLoaded) {
            initCityBackground();
            // Re-align or reset coordinates on resize
            peeps.forEach(p => {
                p.y = canvas.height - (p.height * p.scale) + 75;
            });
        }
    });
    resizeCanvas();

    // Generate minimalistic buildings list and traffic light position
    function initCityBackground() {
        buildings = [];
        const count = 12;
        const baseWidth = 100;
        
        // Custom vertical billboard text options
        const billboardTexts = ["CINEMA", "CAFE-BAR", "SPORT", "MAKE UP", "EXIT 7", "AI-CROWD", "DENSITY"];

        for (let i = 0; i < count; i++) {
            const w = Math.random() * 50 + baseWidth;
            const h = Math.random() * 200 + 130; // building height range
            const x = (i * (canvas.width / (count - 1))) - (w / 2);
            
            const windowRows = Math.floor(h / 30);
            const windowCols = Math.floor(w / 22);
            
            // Randomize roof profiles, antennas, and billboards
            const styleType = Math.random() > 0.5 ? 'classic' : 'stripe';
            const roofStyles = ['stepped', 'slanted', 'triangle', 'flat'];
            const roofStyle = roofStyles[Math.floor(Math.random() * roofStyles.length)];
            const hasAntenna = Math.random() > 0.6;
            const hasBillboard = Math.random() > 0.7;
            const antennaHeight = hasAntenna ? Math.random() * 30 + 15 : 0;
            const billboardText = billboardTexts[Math.floor(Math.random() * billboardTexts.length)];
            
            buildings.push({ 
                x, w, h, 
                windowRows, windowCols,
                styleType, roofStyle, hasAntenna, antennaHeight,
                hasBillboard, billboardText
            });
        }
        
        // Setup traffic light coordinates on the right side
        trafficLight = {
            x: canvas.width * 0.85,
            y: canvas.height - 250
        };
    }

    // Draw the line-art minimalistic city streets background (darker slate styling)
    function drawCityBackground() {
        ctx.save();
        ctx.strokeStyle = "rgba(15, 23, 42, 0.22)"; // Darker building outlines
        ctx.lineWidth = 1.5;

        // 1. Draw drooping overhead power lines stretching across the street
        ctx.beginPath();
        // Wire 1
        ctx.moveTo(0, 110);
        ctx.bezierCurveTo(canvas.width * 0.33, 170, canvas.width * 0.66, 170, canvas.width, 90);
        // Wire 2
        ctx.moveTo(0, 130);
        ctx.bezierCurveTo(canvas.width * 0.35, 205, canvas.width * 0.68, 200, canvas.width, 115);
        // Wire 3
        ctx.moveTo(0, 160);
        ctx.bezierCurveTo(canvas.width * 0.30, 235, canvas.width * 0.70, 240, canvas.width, 140);
        ctx.stroke();

        // 2. Draw Buildings outline and window grids
        buildings.forEach(b => {
            ctx.beginPath();
            
            // Draw custom rooftop spires and profiles
            if (b.roofStyle === 'stepped') {
                // Stepped crown skyscraper
                ctx.moveTo(b.x, canvas.height);
                ctx.lineTo(b.x, canvas.height - b.h + 40);
                ctx.lineTo(b.x + 15, canvas.height - b.h + 40);
                ctx.lineTo(b.x + 15, canvas.height - b.h);
                ctx.lineTo(b.x + b.w - 15, canvas.height - b.h);
                ctx.lineTo(b.x + b.w - 15, canvas.height - b.h + 40);
                ctx.lineTo(b.x + b.w, canvas.height - b.h + 40);
                ctx.lineTo(b.x + b.w, canvas.height);
            } else if (b.roofStyle === 'slanted') {
                // Slanted profile roof
                ctx.moveTo(b.x, canvas.height);
                ctx.lineTo(b.x, canvas.height - b.h + 30);
                ctx.lineTo(b.x + b.w, canvas.height - b.h);
                ctx.lineTo(b.x + b.w, canvas.height);
            } else if (b.roofStyle === 'triangle') {
                // Triangular pitched roof
                ctx.moveTo(b.x, canvas.height);
                ctx.lineTo(b.x, canvas.height - b.h + 35);
                ctx.lineTo(b.x + (b.w / 2), canvas.height - b.h);
                ctx.lineTo(b.x + b.w, canvas.height - b.h + 35);
                ctx.lineTo(b.x + b.w, canvas.height);
            } else {
                // Flat roof building
                ctx.rect(b.x, canvas.height - b.h, b.w, b.h);
            }
            ctx.stroke();

            // Draw rooftop antenna spires
            if (b.hasAntenna) {
                const antennaX = b.x + (b.w / 2);
                const buildingTopY = canvas.height - (b.roofStyle === 'triangle' ? b.h : b.roofStyle === 'slanted' ? b.h - 15 : b.h);
                ctx.beginPath();
                ctx.moveTo(antennaX, buildingTopY);
                ctx.lineTo(antennaX, buildingTopY - b.antennaHeight);
                ctx.stroke();
                
                // Antenna signal red-ish/slate tip globe
                ctx.fillStyle = "rgba(15, 23, 42, 0.45)";
                ctx.beginPath();
                ctx.arc(antennaX, buildingTopY - b.antennaHeight, 2.5, 0, Math.PI * 2);
                ctx.fill();
            }

            // Draw windows (darker slate fills)
            ctx.fillStyle = "rgba(15, 23, 42, 0.14)";
            if (b.styleType === 'classic') {
                for (let r = 1; r < b.windowRows - 1; r++) {
                    for (let c = 0; c < b.windowCols - 1; c++) {
                        const wx = b.x + 12 + (c * 20);
                        const wy = (canvas.height - b.h) + 16 + (r * 28);
                        
                        // Check stepped top boundaries to prevent floating window artifacts
                        if (b.roofStyle === 'stepped' && wy < canvas.height - b.h + 40 && (wx < b.x + 15 || wx > b.x + b.w - 20)) {
                            continue;
                        }
                        // Check triangular roof boundary
                        if (b.roofStyle === 'triangle' && wy < canvas.height - b.h + 45) {
                            continue;
                        }
                        ctx.fillRect(wx, wy, 8, 12);
                    }
                }
            } else {
                // Vertical structural window bands
                for (let c = 1; c < b.windowCols; c++) {
                    const wx = b.x + (c * 20) - 2;
                    const wyStart = canvas.height - b.h + (b.roofStyle !== 'flat' ? 45 : 15);
                    const wyHeight = b.h - (b.roofStyle !== 'flat' ? 65 : 35);
                    ctx.fillRect(wx, wyStart, 5, wyHeight);
                }
            }

            // Billboards (Times Square style ads with actual texts)
            if (b.hasBillboard) {
                const billY = canvas.height - b.h + 60;
                const billW = b.w - 24;
                const billH = 38;
                
                // Outer billboard frame
                ctx.strokeRect(b.x + 12, billY, billW, billH);
                ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
                ctx.fillRect(b.x + 12, billY, billW, billH);
                
                // Inner content line
                ctx.strokeStyle = "rgba(15, 23, 42, 0.12)";
                ctx.strokeRect(b.x + 15, billY + 3, billW - 6, billH - 6);
                
                // Billboard Ad Text
                ctx.fillStyle = "rgba(15, 23, 42, 0.65)";
                ctx.font = "bold 8px 'Inter', sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(b.billboardText, b.x + (b.w / 2), billY + (billH / 2));
                
                // Reset main outline style
                ctx.strokeStyle = "rgba(15, 23, 42, 0.22)";
            }

            // Entrance doors at ground level
            ctx.strokeRect(b.x + (b.w / 2) - 10, canvas.height - 20, 20, 20);
        });

        // Draw Street Crosswalk (Zebra Crossing) at the bottom
        ctx.fillStyle = "rgba(15, 23, 42, 0.05)"; // Darker crossing lines
        const stripeWidth = 60;
        const stripeGap = 40;
        const stripeHeight = 60;
        const startY = canvas.height - stripeHeight;
        
        for (let x = -50; x < canvas.width + 50; x += stripeWidth + stripeGap) {
            ctx.beginPath();
            ctx.moveTo(x, canvas.height);
            ctx.lineTo(x + 20, startY);
            ctx.lineTo(x + 20 + stripeWidth, startY);
            ctx.lineTo(x + stripeWidth, canvas.height);
            ctx.fill();
        }

        // Draw Traffic Light Pole (darker outline)
        const tx = trafficLight.x;
        const ty = trafficLight.y;

        ctx.beginPath();
        // Vertical post
        ctx.moveTo(tx, canvas.height);
        ctx.lineTo(tx, ty);
        // Arm
        ctx.lineTo(tx - 35, ty + 10);
        ctx.stroke();

        // Traffic Light box outline
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.rect(tx - 45, ty + 10, 20, 50);
        ctx.fill();
        ctx.stroke();

        // 3 light indicators (Red light is lit up!)
        const lightColors = ["rgba(239, 68, 68, 0.8)", "rgba(156, 163, 175, 0.2)", "rgba(16, 185, 129, 0.2)"];
        lightColors.forEach((color, idx) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(tx - 35, ty + 20 + (idx * 14), 4, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
        });

        ctx.restore();
    }

    // Peep Character class
    class Peep {
        constructor() {
            this.reset(true);
        }

        reset(initial = false) {
            // Setup larger size scales (0.35 to 0.75) to show full bodies clearly
            this.scale = Math.random() * 0.4 + 0.35; 
            this.width = spriteWidth;
            this.height = spriteHeight;

            // Speed relative to size (larger objects are in foreground, move faster)
            this.speed = (this.scale * 0.6) + Math.random() * 0.25;
            
            // Random direction
            this.direction = Math.random() > 0.5 ? 1 : -1; // 1 = right, -1 = left

            // Position
            if (initial) {
                // Spread evenly across canvas on startup
                this.x = Math.random() * canvas.width;
            } else {
                // Spawn offscreen depending on direction
                this.x = this.direction === 1 ? -260 : canvas.width + 260;
            }

            // Lock to floor (base y-coord pushed 75px down to sink sprites and hide bottom cut lines)
            this.y = canvas.height - (this.height * this.scale) + 75;

            // Character index (row in sprite sheet)
            this.peepIndex = Math.floor(Math.random() * rows);
            
            // Column index (column in sprite sheet - keeps the same character silhouette)
            this.frameIndex = Math.floor(Math.random() * cols);
            
            // Bobbing offset (for walking cycle simulation)
            this.bobOffset = Math.random() * Math.PI * 2;
        }

        update() {
            // Horizontal travel
            this.x += this.speed * this.direction;

            // Out-of-bounds cleanup & respawn
            if (this.direction === 1 && this.x > canvas.width + 260) {
                this.reset(false);
            } else if (this.direction === -1 && this.x < -260) {
                this.reset(false);
            }
        }

        draw() {
            if (!isLoaded) return;

            ctx.save();
            
            // Flip sprite horizontally if walking left
            if (this.direction === -1) {
                ctx.translate(this.x + (this.width * this.scale), 0);
                ctx.scale(-1, 1);
                ctx.translate(-this.x, 0);
            }

            // Bouncy bobbing motion to simulate walk cycle (always bouncing upward)
            const bob = -Math.abs(Math.sin((this.x * 0.06) + this.bobOffset)) * (14 * this.scale);
            const drawX = this.x;
            const drawY = this.y + bob;

            // Draw sprite frame on canvas
            ctx.drawImage(
                img,
                this.frameIndex * this.width,
                this.peepIndex * this.height,
                this.width,
                this.height,
                drawX,
                drawY,
                this.width * this.scale,
                this.height * this.scale
            );

            ctx.restore();
        }
    }

    // Initialize Peeps list
    function initCrowd() {
        peeps = [];
        // Spawn more characters to create a heavily crowded scene (up to 180)
        const densityCount = Math.min(180, Math.floor(window.innerWidth / 9));
        for (let i = 0; i < densityCount; i++) {
            peeps.push(new Peep());
        }
        
        // Sort peeps by scale so background characters (smaller) are drawn first
        peeps.sort((a, b) => a.scale - b.scale);
    }

    // Main Loop
    function animateCrowd() {
        if (!isTabActive) return;

        // Clear canvas with transparent alpha
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw street line art background
        drawCityBackground();

        // Update and render each character
        peeps.forEach(p => {
            p.update();
            p.draw();
        });

        animationFrameId = requestAnimationFrame(animateCrowd);
    }

    // Performance Visibility listeners
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            isTabActive = false;
            cancelAnimationFrame(animationFrameId);
        } else {
            isTabActive = true;
            animateCrowd();
        }
    });
});
