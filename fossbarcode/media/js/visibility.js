function toggle_visibility(id) {
    var e = document.getElementById(id);
    if (typeof e != 'undefined') {
        if (e.style.display == 'block')
            e.style.display = 'none';
        else
            e.style.display = 'block';
    }
}
function show_none(id) {
    var e = document.getElementById(id);
    if (typeof e != 'undefined')
        e.style.display = '';
}
function show_block(id) {
    var e = document.getElementById(id);
    if (typeof e != 'undefined')
        e.style.display = 'block';
}
function hide_element(id) {
    var e = document.getElementById(id);
    if (typeof e != 'undefined')
        e.style.display = 'none';
}

