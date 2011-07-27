function check_for_record() {
    xmlhttp = new XMLHttpRequest();
    var query = "company=" + document.getElementById('id_company').value;
    query += ";product=" + document.getElementById('id_product').value;
    query += ";version=" + document.getElementById('id_version').value;
    query += ";release=" + document.getElementById('id_release').value;
    xmlhttp.open("GET", "/barcode/search_dupes?" + query, false);
    xmlhttp.send();
    return xmlhttp.responseText;
}

