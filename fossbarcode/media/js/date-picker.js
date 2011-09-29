// date picker used on input tab and modal header edit

$(function() {
    $("#id_release_date").datepicker({
        dateFormat: 'yy-mm-dd',
        autoSize: true,
        showOn: "button",
        buttonImage: "/site_media/images/calendar.gif",
        buttonImageOnly: true,
        onSelect: function(dateText, inst) {
            var curDate = new Date();
            var curYear = curDate.getFullYear();
            var curMonth = curDate.getMonth() + 1;
            curMonth = ( curMonth < 10 ? "0" : "" ) + curMonth;
            var curDay = curDate.getDate();
            curDay = ( curDay < 10 ? "0" : "" ) + curDay;
            var curValue = Date.parse(curYear + "-" + curMonth + "-" + curDay);
            var selValue = Date.parse(dateText);
            if (selValue < curValue) {
                if (!confirm("Date is in the past, continue?"))
                    this.value = '';
            } 
        }
    });
});

