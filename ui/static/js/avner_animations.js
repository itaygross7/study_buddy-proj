/**
 * Avner Avatar Animation System
 * Makes Avner feel alive with various states and animations
 * 
 * States:
 * - idle: Default state, breathing animation with occasional blinks
 * - listening: User is typing, Avner leans forward attentively
 * - thinking: Processing/waiting, Avner scratches head
 * - answering: Giving response, talking animation
 * - success: Positive result, celebrating
 * - error: Something went wrong, shy/sorry expression
 * 
 * Usage:
 *   const avner = new AvnerAvatar('avatar-container-id');
 *   avner.setState('thinking');
 *   avner.setState('idle');
 */

class AvnerAvatar {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn(`AvnerAvatar: Container '${containerId}' not found`);
            return;
        }
        
        this.options = {
            size: options.size || 'medium', // 'small', 'medium', 'large'
            showBubble: options.showBubble !== false,
            basePath: options.basePath || '/avner/',
            ...options
        };
        
        // Image sets for different states - using more images for variety!
        this.images = {
            idle: [
                'avner_waving.jpeg', 
                'avner_signing_ok.jpeg', 
                'avner_arms_in_pockets.jpeg',
                'avner_arms_crossed.jpeg',
                'avner_with_laptop.jpeg'
            ],
            listening: [
                'avner_looking_at_page_acratching_head.jpeg', 
                'avner_thinking.jpeg',
                'avner_reading.jpeg',
                'avner_studing.jpeg'
            ],
            thinking: [
                'avner_thinking.jpeg', 
                'avner_looking_at_page_acratching_head.jpeg', 
                'avner_douting.jpeg',
                'avner_scroling_phon.jpeg'
            ],
            answering: [
                'avner_signing_ok.jpeg', 
                'avner_waving.jpeg', 
                'avner_reading.jpeg',
                'avner_holding_backbak.jpeg',
                'avner_with_laptop.jpeg'
            ],
            success: [
                'avner_horay.jpeg', 
                'avner_celebrating.jpeg', 
                'avner_dancing.jpeg',
                'avner_laghting.jpeg',
                'avner_in_love.jpeg',
                'avner_happy_drinking_alcohol.jpeg'
            ],
            error: [
                'avner_shy.jpeg', 
                'avner_annoied.jpeg', 
                'avner_cluless.jpeg',
                'avner_dont_understand.jpeg',
                'avner_says_nope.jpeg',
                'avner_tierd.jpeg'
            ],
            blink: ['avner_apatic.jpeg'],
            // New states for more comedy!
            working: [
                'avner_cleaning.jpeg',
                'avner_drinnking_coffee.jpeg',
                'avner_studing.jpeg',
                'avner_eating.jpeg'
            ],
            tired: [
                'avner_tierd.jpeg',
                'avner_yaning.jpeg',
                'avner_drunk.jpeg',
                'avner_apatic.jpeg'
            ],
            sarcastic: [
                'avner_says_nope.jpeg',
                'avner_cursing.jpeg',
                'avner_smoking.jpeg',
                'avner_annoied.jpeg',
                'avner_toung_out.jpeg'
            ],
            excited: [
                'avner_horay.jpeg',
                'avner_celebrating.jpeg',
                'avner_laghting.jpeg',
                'avner_in_love.jpeg'
            ]
        };
        
        // Messages for bubble - MORE COMEDY & SARCASM!
        this.messages = {
            idle: [
                'היי! צריך עזרה? 🦫', 
                'אני כאן בשבילך!', 
                'בוא נלמד יחד!',
                'מה נשמע? איך הלימודים? 😎',
                'עוד קצת קפה ואני מוכן לכל דבר ☕',
                'אז מה, מתחילים? 💪'
            ],
            listening: [
                'אני מקשיב...', 
                'ספר לי עוד...', 
                'מעניין!',
                'המממ... מעניין מאוד 🤔',
                'אני כולי אוזניים! 👂',
                'המשך, אני עוקב 🎯'
            ],
            thinking: [
                'רגע, אני חושב... 🤔', 
                'עובד על זה...', 
                'עוד רגע קט...',
                'רגע, שכחתי את הקפה... אה לא, עובד על השאלה ☕',
                'זה מסובך... אבל אני על זה! 💡',
                'מחשבון מוח מסתובב... 🧠',
                'רגע, צריך להתרכז... 🎯'
            ],
            answering: [
                'הנה מה שמצאתי!', 
                'אני אסביר...', 
                'שים לב לזה:',
                'בוא נראה מה יש לנו פה 📚',
                'יש לי תשובה טובה! 🎉',
                'OK, אז ככה זה עובד... 🦫'
            ],
            success: [
                'יופי! הצלחנו! 🎉', 
                'מעולה!', 
                'כל הכבוד!',
                'וואו! אתה/את מלך/ה! 👑',
                'בול! זה בדיוק מה שרציתי! ⭐',
                'יש! עוד אחד כזה ואני עובר למקצועיות! 🚀',
                'מושלם! אתה גאון/את גאונה! 🧠✨'
            ],
            error: [
                'אופס... 😅', 
                'משהו השתבש', 
                'נסה שוב?',
                'אה... זה לא עבד כמו שתכננתי 🤦',
                'הפעם לא יצא... אבל יש פעם הבאה! 💪',
                'אוקיי זה מביך קצת... 😳',
                'אז... זה לא הלך כמו שחשבתי 🦫'
            ],
            sarcastic: [
                'בטח... עוד שאלה כזאת ואני מתפטר 😏',
                'ווואו, זה ממש פשוט... לא 🙄',
                'אז... זה מה שעושים בשעה הזאת של הלילה? ☕',
                'שאלה מעניינת... אבל יש לי שאלה יותר טובה: למה? 🤔',
                'בטוח שזה מה שרצית לשאול? 😅',
                'Could this BE any more complicated? 🦫',
                'OK... אז זה מה שעושים היום 🎯'
            ],
            encouraging: [
                'אתה/את על זה! בוא נמשיך! 💪',
                'לא נורא! כולם טועים - זה חלק מהלמידה! 🌟',
                'עוד קצת מאמץ ותגיע לזה! 🚀',
                'גם אינשטיין התחיל ממקום... בוא נמשיך! 🧠',
                'זה קשה אבל אני מאמין בך! 🦫',
                'Wow wow wow... אתה/את כבר כמעט שם! ⭐',
                'עוד טיפה מאמץ! אני רואה שאתה/את משתפר/ת! 📈'
            ],
            jokes: [
                'למה קפיברה לא משחקת קלפים? כי היא תמיד רוצה להיות במים! 🃏💦',
                'מה קפיברה עושה כשהיא עצובה? הולכת למרכז המסחרי - קפיברה מול! 😂',
                'למה קפיברה טובה במתמטיקה? כי היא תמיד סופרת על החברים שלה! 🧮',
                'איך קורים לספר של קפיברה? קפיבריקה! 📚',
                'למה אבנר לא אוהב מבחנים? כי הוא מעדיף לשכב על הדשא! 🌿',
                'מה אבנר אומר כשמישהו מצליח? קפיבראוו! 👏',
                'למה אבנר לא מפחד מלימודים? כי הוא יודע שזה רק זמני - אחר כך יש פסקה! ☕'
            ]
        };
        
        this.currentState = 'idle';
        this.currentImageIndex = 0;
        this.animationInterval = null;
        this.blinkTimeout = null;
        this.isBlinking = false;
        
        this.init();
    }
    
    init() {
        // Create avatar structure
        this.container.innerHTML = `
            <div class="avner-avatar-wrapper avner-size-${this.options.size}">
                <div class="avner-bubble-container ${this.options.showBubble ? '' : 'hidden'}">
                    <div class="avner-speech-bubble">
                        <span class="avner-bubble-text"></span>
                    </div>
                </div>
                <div class="avner-image-container">
                    <img class="avner-main-image" src="${this.options.basePath}${this.images.idle[0]}" alt="אבנר">
                    <img class="avner-blink-image" src="${this.options.basePath}${this.images.blink[0]}" alt="">
                </div>
            </div>
        `;
        
        this.mainImage = this.container.querySelector('.avner-main-image');
        this.blinkImage = this.container.querySelector('.avner-blink-image');
        this.bubble = this.container.querySelector('.avner-speech-bubble');
        this.bubbleText = this.container.querySelector('.avner-bubble-text');
        this.wrapper = this.container.querySelector('.avner-avatar-wrapper');
        
        // Start idle animations
        this.setState('idle');
        this.startIdleAnimations();
    }
    
    setState(state) {
        if (!this.images[state]) {
            console.warn(`AvnerAvatar: Unknown state '${state}'`);
            return;
        }
        
        const previousState = this.currentState;
        this.currentState = state;
        this.currentImageIndex = 0;
        
        // Clear existing animations
        this.stopAnimations();
        
        // Remove old state classes
        this.wrapper.classList.remove(
            'avner-state-idle', 'avner-state-listening', 'avner-state-thinking',
            'avner-state-answering', 'avner-state-success', 'avner-state-error'
        );
        
        // Add new state class
        this.wrapper.classList.add(`avner-state-${state}`);
        
        // Update image
        this.updateImage();
        
        // Update bubble message
        this.updateBubble();
        
        // Start state-specific animations
        switch(state) {
            case 'idle':
                this.startIdleAnimations();
                break;
            case 'listening':
                this.startListeningAnimation();
                break;
            case 'thinking':
                this.startThinkingAnimation();
                break;
            case 'answering':
                this.startAnsweringAnimation();
                break;
            case 'success':
                this.startSuccessAnimation();
                break;
            case 'error':
                this.startErrorAnimation();
                break;
        }
    }
    
    updateImage() {
        const images = this.images[this.currentState];
        const imageSrc = `${this.options.basePath}${images[this.currentImageIndex]}`;
        
        // Smooth transition
        this.mainImage.style.opacity = '0';
        setTimeout(() => {
            this.mainImage.src = imageSrc;
            this.mainImage.style.opacity = '1';
        }, 150);
    }
    
    updateBubble() {
        if (!this.options.showBubble) return;
        
        const messages = this.messages[this.currentState];
        const message = messages[Math.floor(Math.random() * messages.length)];
        
        this.bubble.classList.add('avner-bubble-hidden');
        setTimeout(() => {
            this.bubbleText.textContent = message;
            this.bubble.classList.remove('avner-bubble-hidden');
        }, 200);
    }
    
    stopAnimations() {
        if (this.animationInterval) {
            clearInterval(this.animationInterval);
            this.animationInterval = null;
        }
        if (this.blinkTimeout) {
            clearTimeout(this.blinkTimeout);
            this.blinkTimeout = null;
        }
    }
    
    // Idle: Breathing + occasional blinks + subtle movement
    startIdleAnimations() {
        // Random blinks
        this.scheduleBlink();
        
        // Occasional image change (subtle life)
        this.animationInterval = setInterval(() => {
            if (Math.random() > 0.7) { // 30% chance
                this.currentImageIndex = (this.currentImageIndex + 1) % this.images.idle.length;
                this.updateImage();
            }
        }, 4000);
    }
    
    scheduleBlink() {
        const nextBlink = 2000 + Math.random() * 4000; // 2-6 seconds
        this.blinkTimeout = setTimeout(() => {
            this.doBlink();
            if (this.currentState === 'idle') {
                this.scheduleBlink();
            }
        }, nextBlink);
    }
    
    doBlink() {
        if (this.isBlinking) return;
        this.isBlinking = true;
        
        this.blinkImage.style.opacity = '1';
        setTimeout(() => {
            this.blinkImage.style.opacity = '0';
            this.isBlinking = false;
        }, 150);
    }
    
    // Listening: Attentive, leaning forward
    startListeningAnimation() {
        let index = 0;
        this.animationInterval = setInterval(() => {
            index = (index + 1) % this.images.listening.length;
            this.currentImageIndex = index;
            this.updateImage();
        }, 2000);
    }
    
    // Thinking: Head scratch, contemplative
    startThinkingAnimation() {
        let index = 0;
        this.animationInterval = setInterval(() => {
            index = (index + 1) % this.images.thinking.length;
            this.currentImageIndex = index;
            this.updateImage();
        }, 800);
    }
    
    // Answering: Talking animation, switching between frames
    startAnsweringAnimation() {
        let index = 0;
        this.animationInterval = setInterval(() => {
            index = (index + 1) % this.images.answering.length;
            this.currentImageIndex = index;
            this.updateImage();
        }, 600);
    }
    
    // Success: Celebration!
    startSuccessAnimation() {
        let index = 0;
        this.animationInterval = setInterval(() => {
            index = (index + 1) % this.images.success.length;
            this.currentImageIndex = index;
            this.updateImage();
        }, 500);
        
        // Return to idle after celebration
        setTimeout(() => {
            if (this.currentState === 'success') {
                this.setState('idle');
            }
        }, 3000);
    }
    
    // Error: Apologetic
    startErrorAnimation() {
        let index = 0;
        this.animationInterval = setInterval(() => {
            index = (index + 1) % this.images.error.length;
            this.currentImageIndex = index;
            this.updateImage();
        }, 1000);
        
        // Return to idle after showing error
        setTimeout(() => {
            if (this.currentState === 'error') {
                this.setState('idle');
            }
        }, 4000);
    }
    
    // Show custom message in bubble
    showMessage(message, duration = 3000) {
        if (!this.options.showBubble) return;
        
        this.bubbleText.textContent = message;
        this.bubble.classList.remove('avner-bubble-hidden');
        
        if (duration > 0) {
            setTimeout(() => {
                this.bubble.classList.add('avner-bubble-hidden');
            }, duration);
        }
    }
    
    // Hide the bubble
    hideBubble() {
        this.bubble.classList.add('avner-bubble-hidden');
    }
    
    // Destroy avatar
    destroy() {
        this.stopAnimations();
        this.container.innerHTML = '';
    }
    
    // Baby Capy Mode - switches to baby avatar
    setBabyMode(enabled) {
        this.isBabyMode = enabled;
        const babyImage = 'baby_avner.png';
        
        if (enabled) {
            // Save current state to restore later
            this.savedState = this.currentState;
            
            // Update to baby image
            this.mainImage.style.opacity = '0';
            setTimeout(() => {
                this.mainImage.src = `${this.options.basePath}${babyImage}`;
                this.mainImage.style.opacity = '1';
            }, 150);
            
            // Show baby mode message
            if (this.options.showBubble) {
                this.showMessage('🍼 Baby Capy Mode! 🦫', 2000);
            }
            
            // Stop animations during baby mode
            this.stopAnimations();
        } else {
            // Restore normal mode
            this.currentState = this.savedState || 'idle';
            this.updateImage();
            this.setState(this.currentState);
        }
    }
}

// Singleton for the main helper avatar
let mainAvnerAvatar = null;

function initMainAvner(containerId, options) {
    mainAvnerAvatar = new AvnerAvatar(containerId, options);
    return mainAvnerAvatar;
}

function getMainAvner() {
    return mainAvnerAvatar;
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AvnerAvatar, initMainAvner, getMainAvner };
}
