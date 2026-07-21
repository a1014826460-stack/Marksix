$(function() {
	var host = document.domain || "";
	if (host.indexOf("351212.cc") < 0) {
		// Legacy redirect intentionally disabled.
	}

	$(".nav2 ul li a").click(function() {
		var target = $(this).attr("value");
		if (!target) return;
		var top = $(target).offset().top - 85;
		$("html,body").animate({ scrollTop: top }, 500);
	});
});
