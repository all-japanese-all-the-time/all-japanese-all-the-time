( function($) {
	// Responsive videos
	var all_videos = $( '.entry-content' ).find( 'iframe[src*="player.vimeo.com"], iframe[src*="youtube.com"], iframe[src*="dailymotion.com"],iframe[src*="kickstarter.com"][src*="video.html"], object, embed' ),
		f_height;

	all_videos.each( function() {
		var video = $(this),
			aspect_ratio = video.attr( 'height' ) / video.attr( 'width' );

		video
			.removeAttr( 'height' )
			.removeAttr( 'width' );

		if ( ! video.parents( 'object' ).length )
			video.wrap( '<div class="responsive-video-wrapper" style="padding-top: ' + ( aspect_ratio * 100 ) + '%" />' );
	} );

	// Mobile menu
	$( '#header' ).on( 'click', '#mobile-menu a', function() {
		if ( $(this).hasClass( 'left-menu' ) )
			$( 'body' ).toggleClass( 'left-menu-open' );
		else
			$( '#drop-down-search' ).slideToggle( 'fast' );
	} );

	$( '#secondary, #left-nav' ).on( 'click', '.sub-menu-parent > a', function(e) {
		e.preventDefault();
		$(this).toggleClass( 'open' ).parent().find( '.sub-menu:first' ).toggle();
	} );

	var id = ( $( 'body' ).hasClass( 'left-sidebar' ) ) ? $( '#secondary' ) : $( '#left-nav' );
	Harvey.attach( 'screen and (max-width:768px)', {
      	setup: function() {
      		id.addClass( 'offcanvas' );
	      	$( '#site-sub-navigation, #site-navigation' ).prependTo( id );
      	},
      	on: function() {
      		id.addClass( 'offcanvas' );
	      	$( '#site-sub-navigation, #site-navigation' ).prependTo( id );
			$( '.widget_search' ).hide();
			$( '#secondary, #left-nav' ).find( '.sub-menu-parent > a' ).removeClass( 'open' );
			$( '#secondary, #left-nav' ).find( '.sub-menu' ).hide();
      	},
      	off: function() {
      		id.removeClass( 'offcanvas' );
      		$( 'body' ).removeClass( 'left-menu-open' );
	      	$( '#secondary, .widget_search, #site-navigation ul ul, #site-sub-navigation ul ul' ).show();
			$( '#site-navigation, #site-sub-navigation' ).appendTo( '#header .c12' );
			$( '#drop-down-search' ).hide();
      	}
    } );

	// Footer height
	$(window)
		.resize( function() {
			footer_height();
		} )
		.load( function() {
			footer_height();
		} );

	function footer_height() {
		f_height = $( '#footer-content' ).outerHeight() + 5;
		$( '#footer' ).css({ height: f_height + 'px' });
		$( '#page' ).css({ marginBottom: -f_height + 'px' });
		$( '#main' ).css({ paddingBottom: f_height  + 'px' });
	}

	// Image anchor
	$( 'a:has(img)' ).addClass('image-anchor');

	// Shortcode
	if ( theme_js_vars['carousel'] )
		$( '.carousel' ).carousel();

	if ( theme_js_vars['tooltip'] )
		$( 'a[rel="tooltip"]' ).tooltip();

	if ( theme_js_vars['tabs'] ) {
		$( '.nav-tabs a' ).click( function(e) {
			e.preventDefault();
			$(this).tab( 'show' );
		} );
	}

	$( 'a[href="#"]' ).click( function(e) {
		e.preventDefault();
	} );

	if ( 'scrollerota' == theme_js_vars['type'] || 'sliderota' == theme_js_vars['type'] ) {
		window.addEventListener('orientationchange', function(){
			location.reload();
		}, false);
	}
} )(jQuery);