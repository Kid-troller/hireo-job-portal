// Gamification Interactive Features
document.addEventListener('DOMContentLoaded', function() {
    initializeGamification();
});

function initializeGamification() {
    // Achievement filtering
    initializeAchievementFilters();
    
    // Auto-refresh stats every 30 seconds
    setInterval(refreshStats, 30000);
    
    // Initialize tooltips
    initializeTooltips();
    
    // Simulate achievement unlock for demo
    setTimeout(() => {
        if (Math.random() > 0.7) {
            showAchievementUnlock('Profile Master', 'You completed your profile!');
        }
    }, 5000);
}

function initializeAchievementFilters() {
    const filterButtons = document.querySelectorAll('.achievement-filters button');
    const achievements = document.querySelectorAll('.achievement-badge');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            filterButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            
            const filter = this.getAttribute('data-filter');
            
            achievements.forEach(achievement => {
                if (filter === 'all') {
                    achievement.parentElement.style.display = 'block';
                } else {
                    const category = achievement.getAttribute('data-category');
                    if (category === filter) {
                        achievement.parentElement.style.display = 'block';
                    } else {
                        achievement.parentElement.style.display = 'none';
                    }
                }
            });
        });
    });
}

function showMotivationalModal() {
    const modal = new bootstrap.Modal(document.getElementById('motivationalModal'));
    modal.show();
}

function showAchievementUnlock(title, description) {
    const unlockElement = document.getElementById('achievementUnlock');
    const unlockText = document.getElementById('unlockText');
    
    unlockText.textContent = description;
    unlockElement.style.display = 'flex';
    
    // Play achievement sound (if available)
    playAchievementSound();
}

function closeAchievementUnlock() {
    const unlockElement = document.getElementById('achievementUnlock');
    unlockElement.style.display = 'none';
}

function playAchievementSound() {
    // Create a simple achievement sound using Web Audio API
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(523.25, audioContext.currentTime); // C5
        oscillator.frequency.setValueAtTime(659.25, audioContext.currentTime + 0.1); // E5
        oscillator.frequency.setValueAtTime(783.99, audioContext.currentTime + 0.2); // G5
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
        console.log('Audio not supported');
    }
}

function refreshStats() {
    // Simulate stat updates
    const xpElement = document.querySelector('.stat-item strong');
    if (xpElement) {
        const currentXP = parseInt(xpElement.textContent);
        const newXP = currentXP + Math.floor(Math.random() * 10);
        xpElement.textContent = newXP;
    }
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips for achievement badges
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Skill Challenge Functions
function startSkillChallenge(skill) {
    alert(`Starting ${skill} challenge! This would redirect to the skill assessment page.`);
}

// Leaderboard Functions
function viewFullLeaderboard() {
    alert('This would show the full leaderboard with all users!');
}

// Career Milestone Functions
function viewMilestoneDetails(milestone) {
    alert(`Viewing details for: ${milestone}`);
}

// XP Animation
function animateXPGain(amount) {
    const xpElement = document.querySelector('.stat-item strong');
    if (xpElement) {
        const floatingXP = document.createElement('div');
        floatingXP.className = 'floating-xp';
        floatingXP.textContent = `+${amount} XP`;
        floatingXP.style.cssText = `
            position: absolute;
            color: #28a745;
            font-weight: bold;
            animation: floatUp 2s ease-out forwards;
            pointer-events: none;
            z-index: 1000;
        `;
        
        xpElement.parentElement.appendChild(floatingXP);
        
        setTimeout(() => {
            floatingXP.remove();
        }, 2000);
    }
}

// Add CSS for floating XP animation
const style = document.createElement('style');
style.textContent = `
    @keyframes floatUp {
        0% {
            transform: translateY(0);
            opacity: 1;
        }
        100% {
            transform: translateY(-50px);
            opacity: 0;
        }
    }
    
    .floating-xp {
        animation: floatUp 2s ease-out forwards;
    }
`;
document.head.appendChild(style);
