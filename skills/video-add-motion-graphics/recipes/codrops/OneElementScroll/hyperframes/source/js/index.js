import { preloadImages } from './utils.js'; // Import utility function to preload images

gsap.registerPlugin(ScrollTrigger, Flip); // Register GSAP's ScrollTrigger and Flip plugins

// Select the element that will be animated with Flip and its parent
const oneElement = document.querySelector('.one');
const parentElement = oneElement.parentNode;

// Select all elements with a `data-step` attribute for the Flip animation steps
const stepElements = [...document.querySelectorAll('[data-step]')];

let flipCtx; // Variable to store the Flip animation context

// Function to create a Flip animation tied to scroll events
const createFlipOnScrollAnimation = () => {
  // Revert any previous animation context
  flipCtx && flipCtx.revert();

  flipCtx = gsap.context(() => {
    const flipConfig = {
      duration: 1, // Duration of each Flip animation
      ease: 'sine.inOut' // Easing for smooth transitions
    };

    // Store Flip states for each step element
    const states = stepElements.map(stepElement => Flip.getState(stepElement));

    // Create a GSAP timeline with ScrollTrigger for the Flip animation
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: parentElement, // Trigger animation based on the parent element
        start: 'clamp(center center)', // Start animation when parent is in the center of the viewport
        endTrigger: stepElements[stepElements.length - 1], // End at the last step element
        end: 'clamp(center center)', // End animation when the last step is centered
        scrub: true, // Synchronize animation with scroll
        immediateRender: false
      }
    });

    // Add Flip animations to the timeline for each state
    states.forEach((state, index) => {
      const customFlipConfig = {
        ...flipConfig,
        ease: index === 0 ? 'none' : flipConfig.ease // Use 'none' easing for the first step
      };
      tl.add(Flip.fit(oneElement, state, customFlipConfig), index ? '+=0.5' : 0);
    });
  });
};

// Animate spans within `.content__title` elements on scroll
const animateSpansOnScroll = () => {
  const spans = document.querySelectorAll('.content__title > span'); // Select all spans

    spans.forEach((span, index) => {
      const direction = index % 2 === 0 ? -150 : 150; // Alternate direction for animation

      // Determine the scroll trigger dynamically based on the parent section
      const triggerElement = span.closest('.content--center') ? span.parentNode : span;

      gsap.from(span, {
        x: direction, // Animate from the left or right
        duration: 1,
        ease: 'sine', // Smooth easing
        scrollTrigger: {
          trigger: triggerElement, // Trigger element
          start: 'top bottom', // Start animation when element enters viewport
          end: '+=45%', // End animation after 45% of the viewport
          scrub: true, // Synchronize with scroll
        },
      });
    });
};

// Animate specific images on scroll
const animateImagesOnScroll = () => {
  const images = document.querySelectorAll('.content--lines .content__img:not([data-step]), .content--grid .content__img:not([data-step])');

  images.forEach((image) => {
    gsap.fromTo(image, { 
      scale: 0, // Start small
      autoAlpha: 0, // Start transparent
      filter: 'brightness(180%) saturate(0%)' // Start desaturated and bright
    }, {
      scale: 1, // Scale to full size
      autoAlpha: 1, // Fade in
      filter: 'brightness(100%) saturate(100%)', // Restore normal brightness and saturation
      duration: 1,
      ease: 'sine', // Smooth easing
      scrollTrigger: {
        trigger: image,
        start: 'top bottom', // Start animation when element enters viewport
        end: '+=45%', // End animation after 45% of the viewport
        scrub: true,
      },
    });
  });
};

// Add a parallax effect to `.content__text` elements
const addParallaxToText = () => {
  const firstTextElement = document.querySelector('.content__text'); // Select the first text element
  if (!firstTextElement) return; // Exit if no element is found

  gsap.fromTo(
    firstTextElement, { 
      y: 250, // Start below its original position
    }, {
      y: -250, // Move above its original position
      ease: 'sine', // Smooth easing
      scrollTrigger: {
        trigger: firstTextElement,
        start: 'top bottom', // Start when top of element enters viewport
        end: 'top top', // End when top of element reaches top of viewport
        scrub: true, // Synchronize with scroll
      },
    }
  );
};

// Animate the filter effect on the `.one` element during the first scroll
const animateFilterOnFirstSwitch = () => {
  gsap.fromTo(oneElement, { 
    filter: 'brightness(80%)' // Start with high brightness and reduced saturation
  }, {
    filter: 'brightness(100%)', // Transition to normal state
    ease: 'sine', // Smooth easing
    scrollTrigger: {
      trigger: parentElement, 
      start: 'clamp(top bottom)', // Start when parent enters viewport
      end: 'clamp(bottom top)', // End when parent leaves viewport
      scrub: true, 
    }
  });
};

// Add a parallax effect to images in the `.content--column` section
const addParallaxToColumnImages = () => {
  const columnImages = [...document.querySelectorAll('.content--column .content__img:not([data-step])')];
  const totalImages = columnImages.length;
  const middleIndex = (totalImages - 1) / 2; // Calculate the virtual center index for symmetry

  columnImages.forEach((image, index) => {
    const intensity = Math.abs(index - middleIndex) * 75; // Calculate intensity based on distance from center

    gsap.fromTo(image, { 
      y: intensity // Start with offset based on intensity
    }, {
      y: -intensity, // Move in the opposite direction
      ease: 'sine', // Smooth easing
      scrollTrigger: {
        trigger: image,
        start: 'top bottom', // Start when top of element enters viewport
        end: 'bottom top', // End when bottom of element leaves viewport
        scrub: true, 
      },
    });
  });
};

const animateRelatedDemos = () => {
  const relatedSection = document.querySelector('.card-wrap');
  const relatedDemos = [...relatedSection.querySelectorAll('.card-wrap > .card')];

  gsap.from(relatedDemos, {
    scale: 0,
    ease: 'sine',
    stagger: {
      each: 0.04,
      from: 'center'
    },
    scrollTrigger: {
      trigger: relatedSection,
      start: 'top bottom', 
      end: 'clamp(center center)', 
      scrub: true, 
    },
  });
};

// Main initialization function
const init = () => {
  createFlipOnScrollAnimation(); // Initialize Flip animations
  animateSpansOnScroll(); // Animate spans on scroll
  animateImagesOnScroll(); // Animate images on scroll
  addParallaxToText(); // Add parallax effect to text
  addParallaxToColumnImages(); // Add parallax effect to column images
  animateFilterOnFirstSwitch(); // Animate the filter on the `.one` element
  animateRelatedDemos(); // Animate the related demos section
  window.addEventListener('resize', createFlipOnScrollAnimation); // Reinitialize Flip animations on resize
};

// Preload images and initialize animations after images have loaded
preloadImages('.one__img').then(() => {
  document.body.classList.remove('loading'); // Remove the 'loading' class from the body
  init(); // Initialize animations
});
