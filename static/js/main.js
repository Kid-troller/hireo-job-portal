// Main JavaScript file for Hireo Job Portal

$(document).ready(function() {
    // Let Bootstrap handle dropdowns automatically - no manual initialization needed

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if (target.length) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 70
            }, 1000);
        }
    });

    // Add fade-in animation to cards
    $('.card').addClass('fade-in');

    // Add slide-in animations based on scroll position
    $(window).scroll(function() {
        $('.feature-icon, .stat-item').each(function() {
            var elementTop = $(this).offset().top;
            var elementBottom = elementTop + $(this).outerHeight();
            var viewportTop = $(window).scrollTop();
            var viewportBottom = viewportTop + $(window).height();

            if (elementBottom > viewportTop && elementTop < viewportBottom) {
                $(this).addClass('slide-in-left');
            }
        });
    });

    // Form validation enhancement
    $('form').on('submit', function() {
        var $form = $(this);
        var $submitBtn = $form.find('button[type="submit"]');
        var originalText = $submitBtn.text();

        // Show loading state
        $submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2"></span>Processing...');

        // Re-enable button after 5 seconds (fallback)
        setTimeout(function() {
            $submitBtn.prop('disabled', false).text(originalText);
        }, 5000);
    });

    // Auto-hide alerts after 5 seconds
    $('.alert').delay(5000).fadeOut(1000);

    // Enhanced search functionality
    $('#searchForm').on('submit', function(e) {
        var query = $('#searchQuery').val().trim();
        var location = $('#searchLocation').val().trim();

        if (!query && !location) {
            e.preventDefault();
            showNotification('Please enter at least a job title or location', 'warning');
            return false;
        }
    });

    // Save job functionality
    $('.save-job-btn').on('click', function(e) {
        e.preventDefault();
        var $btn = $(this);
        var jobId = $btn.data('job-id');
        var $icon = $btn.find('i');

        $.ajax({
            url: '/accounts/save-job/' + jobId + '/',
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(response) {
                if (response.success) {
                    if (response.action === 'saved') {
                        $icon.removeClass('fa-bookmark-o').addClass('fa-bookmark');
                        $btn.addClass('btn-success').removeClass('btn-outline-success');
                        showNotification(response.message, 'success');
                    } else {
                        $icon.removeClass('fa-bookmark').addClass('fa-bookmark-o');
                        $btn.removeClass('btn-success').addClass('btn-outline-success');
                        showNotification(response.message, 'info');
                    }
                }
            },
            error: function() {
                showNotification('An error occurred. Please try again.', 'error');
            }
        });
    });

    // Job application form enhancement
    $('.job-application-form').on('submit', function(e) {
        var $form = $(this);
        var $submitBtn = $form.find('button[type="submit"]');
        var originalText = $submitBtn.text();

        // Validate file size
        var resumeFile = $form.find('input[name="resume"]')[0].files[0];
        if (resumeFile && resumeFile.size > 5 * 1024 * 1024) { // 5MB
            e.preventDefault();
            showNotification('Resume file size must be less than 5MB', 'error');
            return false;
        }

        // Show loading state
        $submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2"></span>Submitting...');
    });

    // Dynamic form fields for education/experience
    $('.add-education-btn').on('click', function() {
        var $container = $('.education-fields');
        var fieldCount = $container.find('.education-field').length;
        var newField = `
            <div class="education-field border rounded p-3 mb-3">
                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label">Institution</label>
                        <input type="text" class="form-control" name="education[${fieldCount}][institution]" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Field of Study</label>
                        <input type="text" class="form-control" name="education[${fieldCount}][field_of_study]" required>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-md-4">
                        <label class="form-label">Start Date</label>
                        <input type="date" class="form-control" name="education[${fieldCount}][start_date]" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">End Date</label>
                        <input type="date" class="form-control" name="education[${fieldCount}][end_date]">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Degree Type</label>
                        <select class="form-control" name="education[${fieldCount}][degree_type]" required>
                            <option value="">Select Degree</option>
                            <option value="high_school">High School</option>
                            <option value="associate">Associate Degree</option>
                            <option value="bachelor">Bachelor Degree</option>
                            <option value="master">Master Degree</option>
                            <option value="phd">PhD</option>
                            <option value="certification">Certification</option>
                        </select>
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-danger mt-2 remove-field-btn">Remove</button>
            </div>
        `;
        $container.append(newField);
    });

    // Remove dynamic form fields
    $(document).on('click', '.remove-field-btn', function() {
        $(this).closest('.education-field').remove();
    });

    // Job search filters
    $('.job-filter').on('change', function() {
        var $form = $(this).closest('form');
        var $results = $('.job-results');
        var $loading = $('.loading-indicator');

        $loading.show();
        $results.hide();

        $.ajax({
            url: $form.attr('action'),
            method: 'GET',
            data: $form.serialize(),
            success: function(response) {
                $results.html(response).show();
                $loading.hide();
                
                // Update URL without page reload
                var newUrl = window.location.pathname + '?' + $form.serialize();
                window.history.pushState({}, '', newUrl);
            },
            error: function() {
                showNotification('An error occurred while filtering jobs', 'error');
                $loading.hide();
                $results.show();
            }
        });
    });

    // Pagination enhancement
    $('.pagination').on('click', 'a', function(e) {
        e.preventDefault();
        var $link = $(this);
        var url = $link.attr('href');
        var $container = $('.job-results');

        $container.fadeOut(300, function() {
            $.get(url, function(response) {
                $container.html(response).fadeIn(300);
                
                // Update URL
                window.history.pushState({}, '', url);
                
                // Scroll to top
                $('html, body').animate({ scrollTop: 0 }, 500);
            });
        });
    });

    // Profile image upload preview
    $('input[type="file"]').on('change', function() {
        var file = this.files[0];
        var $preview = $('.image-preview');
        
        if (file) {
            var reader = new FileReader();
            reader.onload = function(e) {
                $preview.html(`<img src="${e.target.result}" class="img-fluid rounded" style="max-width: 200px;">`);
            };
            reader.readAsDataURL(file);
        }
    });

    // Skills input enhancement
    $('.skills-input').on('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            var $input = $(this);
            var value = $input.val().trim();
            
            if (value) {
                addSkillTag(value);
                $input.val('');
            }
        }
    });

    // Add skill tag
    function addSkillTag(skill) {
        var $container = $('.skills-tags');
        var tag = `
            <span class="badge bg-primary me-2 mb-2">
                ${skill}
                <i class="fas fa-times ms-1 remove-skill" style="cursor: pointer;"></i>
            </span>
        `;
        $container.append(tag);
    }

    // Remove skill tag
    $(document).on('click', '.remove-skill', function() {
        $(this).parent().remove();
    });

    // Notification system
    function showNotification(message, type) {
        var alertClass = 'alert-' + (type === 'error' ? 'danger' : type);
        var notification = `
            <div class="alert ${alertClass} alert-dismissible fade show position-fixed" 
                 style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('body').append(notification);
        
        // Auto-hide after 5 seconds
        setTimeout(function() {
            $('.position-fixed.alert').fadeOut(500, function() {
                $(this).remove();
            });
        }, 5000);
    }

    // Get CSRF token from cookies
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Lazy loading for images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }

    // Back to top button
    var $backToTop = $('<button class="btn btn-primary position-fixed" style="bottom: 20px; right: 20px; z-index: 999; display: none;">' +
                       '<i class="fas fa-arrow-up"></i></button>');
    $('body').append($backToTop);

    $(window).scroll(function() {
        if ($(this).scrollTop() > 300) {
            $backToTop.fadeIn();
        } else {
            $backToTop.fadeOut();
        }
    });

    $backToTop.on('click', function() {
        $('html, body').animate({ scrollTop: 0 }, 500);
    });

    // Mobile menu enhancement
    $('.navbar-toggler').on('click', function() {
        $(this).toggleClass('active');
    });

    // Form auto-save (for long forms)
    var autoSaveTimer;
    $('form textarea, form input[type="text"]').on('input', function() {
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(function() {
            // Auto-save logic here
            console.log('Auto-saving form...');
        }, 2000);
    });

    // Keyboard shortcuts
    $(document).on('keydown', function(e) {
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            $('#searchQuery').focus();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            $('.modal').modal('hide');
        }
    });

    // Performance optimization: Debounce scroll events
    var scrollTimer;
    $(window).on('scroll', function() {
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(function() {
            // Handle scroll-based animations
            handleScrollAnimations();
        }, 10);
    });

    function handleScrollAnimations() {
        $('.animate-on-scroll').each(function() {
            var elementTop = $(this).offset().top;
            var elementBottom = elementTop + $(this).outerHeight();
            var viewportTop = $(window).scrollTop();
            var viewportBottom = viewportTop + $(window).height();

            if (elementBottom > viewportTop && elementTop < viewportBottom) {
                $(this).addClass('animated');
            }
        });
    }

    // Initialize scroll animations
    handleScrollAnimations();
});
