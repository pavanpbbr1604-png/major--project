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
        // Increase canvas height to 500px for generous bottom clearance
        canvas.height = 500; 
    }
    window.addEventListener("resize", () => {
        resizeCanvas();
        if (isLoaded) {
            initCityBackground();
            // Re-align y coordinates on resize
            peeps.forEach(p => {
                p.y = canvas.height - (p.height * p.scale) - 10;
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

        // Draw Multi-Camera CCTV Security Tower (Matching user reference image & theme)
        const cx = canvas.width * 0.88; // Placed at exact blue sketch position
        const cy = canvas.height - 270;

        ctx.save();
        ctx.strokeStyle = "#0f172a";
        ctx.fillStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.lineJoin = "round";
        ctx.lineCap = "round";

        // 1. Scanning Cone Beams (AI Crowd Surveillance Theme)
        const pulseOpacity = 0.08 + Math.sin(Date.now() * 0.003) * 0.03;
        
        ctx.fillStyle = `rgba(37, 99, 235, ${pulseOpacity})`;
        // Beam from Top Left Camera
        ctx.beginPath();
        ctx.moveTo(cx - 30, cy - 25);
        ctx.lineTo(cx - 200, canvas.height);
        ctx.lineTo(cx - 50, canvas.height);
        ctx.closePath();
        ctx.fill();

        // Beam from Top Right Camera
        ctx.beginPath();
        ctx.moveTo(cx + 45, cy + 5);
        ctx.lineTo(cx + 80, canvas.height);
        ctx.lineTo(cx + 240, canvas.height);
        ctx.closePath();
        ctx.fill();

        // Beam from Middle Right Camera
        ctx.beginPath();
        ctx.moveTo(cx + 35, cy + 65);
        ctx.lineTo(cx - 30, canvas.height);
        ctx.lineTo(cx + 140, canvas.height);
        ctx.closePath();
        ctx.fill();

        // 2. Main Vertical Pole
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.rect(cx - 6, cy - 10, 12, canvas.height - (cy - 10));
        ctx.fill();
        ctx.stroke();

        // 3D side line on pole
        ctx.beginPath();
        ctx.moveTo(cx + 6, cy - 10);
        ctx.lineTo(cx + 10, cy - 5);
        ctx.lineTo(cx + 10, canvas.height);
        ctx.stroke();

        // Pole Top Cap
        ctx.fillStyle = "#0f172a";
        ctx.beginPath();
        ctx.rect(cx - 8, cy - 16, 16, 6);
        ctx.fill();
        ctx.stroke();

        // Helper function to draw a CCTV Security Camera matching reference image
        function drawCamera(camX, camY, angleDeg, scale = 1.0) {
            ctx.save();
            ctx.translate(camX, camY);
            ctx.rotate((angleDeg * Math.PI) / 180);
            ctx.scale(scale, scale);

            // Mounting Plate on pole
            ctx.fillStyle = "#0f172a";
            ctx.fillRect(-2, -12, 6, 24);

            // Mounting Bracket Arm
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.moveTo(0, -6);
            ctx.lineTo(24, -14);
            ctx.lineTo(28, -6);
            ctx.lineTo(24, 6);
            ctx.lineTo(0, 6);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            // Cable wire loop
            ctx.beginPath();
            ctx.moveTo(4, 6);
            ctx.quadraticCurveTo(12, 18, 26, 12);
            ctx.stroke();

            // Camera Housing Box
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.rect(26, -16, 42, 26);
            ctx.fill();
            ctx.stroke();

            // Sunshield / Top Hood
            ctx.fillStyle = "#0f172a";
            ctx.beginPath();
            ctx.moveTo(24, -20);
            ctx.lineTo(72, -20);
            ctx.lineTo(68, -16);
            ctx.lineTo(26, -16);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            // Front Lens Bezel
            ctx.fillStyle = "#0f172a";
            ctx.fillRect(68, -14, 5, 22);

            // Inner Lens Circle
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(70, -3, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = "#0f172a";
            ctx.beginPath();
            ctx.arc(70, -3, 3, 0, Math.PI * 2);
            ctx.fill();

            // Glowing lens core dot (AI camera indicator)
            ctx.fillStyle = "#2563eb";
            ctx.beginPath();
            ctx.arc(70, -3, 1.5, 0, Math.PI * 2);
            ctx.fill();

            // Red LED Status Indicator light on side
            ctx.fillStyle = (Math.floor(Date.now() / 600) % 2 === 0) ? "#ef4444" : "#991b1b";
            ctx.beginPath();
            ctx.arc(32, -10, 2, 0, Math.PI * 2);
            ctx.fill();

            ctx.restore();
        }

        // Camera 1: Top Left (pointing left & down)
        drawCamera(cx - 6, cy - 5, -155, 0.95);

        // Camera 2: Top Right (pointing right & down)
        drawCamera(cx + 6, cy + 15, 18, 0.95);

        // Camera 3: Middle Right (pointing down & right)
        drawCamera(cx + 6, cy + 70, 32, 0.88);

        ctx.restore();
    }

    // Peep Character class
    class Peep {
        constructor() {
            this.reset(true);
        }

        reset(initial = false) {
            // Scale range (0.32 to 0.62) for optimal character proportion
            this.scale = Math.random() * 0.3 + 0.32; 
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

            // Lock to floor cleanly above bottom edge (-10px to -30px margin offset)
            this.y = canvas.height - (this.height * this.scale) - 10 - (Math.random() * 20);

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
