# Create your views here.
from django.template import Context, loader
from django.shortcuts import render_to_response, get_object_or_404
from fossbarcode.barcode.models import Product_Record, FOSS_Components, Patch_Files, System_Settings, RecordForm
from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404
from django.conf import settings

from fossbarcode import task

import sys, os, re, urllib, subprocess, time, datetime

# buffer size for Popen, we want unbuffered
bufsize = -1

# collect the system configuration global defaults - just host_site for now
settings_list = System_Settings.objects.all()
for s in settings_list:
    if s.name == "host_site":
        host_site = s.value
    if s.name == "host_site_in_qrcode":
        host_site_in_qrcode = s.value

### each of these views has a corresponding html page in ../templates/barcode

# task status page - intended for calling in javascript
def taskstatus(request):
    tm = task.TaskManager()
    return HttpResponse(tm.read_status())

# system configuration settings
def sysconfig(request):
    info_message = ""

    if request.method == 'POST': # If the form has been submitted...
        # walk through all the known system settings and update
        # do we need to go back and regenerate all the QR codes if host_site changes?
        ss_list = System_Settings.objects.values('name')    
        for s in ss_list:
            ss_value = request.POST.get(s['name'], '')
            if (ss_value != ""):
                System_Settings.objects.filter(name = s['name']).update(value = ss_value, 
                                               last_updated = str(datetime.date.today()), 
                                               user_updated = True)

        return HttpResponseRedirect('/barcode/input/')

    else:
        # has the user confirmed the settings?
        settings_done = System_Settings.objects.filter(user_updated = True).count()
        if (settings_done) == 0:
            info_message = "You must confirm and save the system settings to continue..."
        
    settings_list = System_Settings.objects.order_by('name')

    return render_to_response('barcode/sysconfig.html', {'info_message': info_message,
                                                        'settings_list': settings_list,
                                                        'host_site': host_site,
                                                        'tab_sysconfig': True })

# record detail page
def detail(request, record_id):
    foss = render_detail(record_id)
    record_list = Product_Record.objects.filter(id = record_id)
    record = record_list[0]
    return render_to_response('barcode/detail.html', {'record': record, 'foss': foss, 'host_site': host_site, 'tab_results': True})

# record change history page
def history(request, record_id):
    record_list = Product_Record.objects.filter(id = record_id)
    record = record_list[0]
    # FIXME - need to do something more useful both here and in the template
    return render_to_response('barcode/history.html', {'record': record})

# line item edit page
def edit_line(request, record_id, item_id):
    item_list = FOSS_Components.objects.filter(brecord = record_id, id = item_id)
    item = item_list[0]
    return render_to_response('barcode/edit_line.html', {'item': item})

# header edit page
def edit_header(request, record_id):
    record_list = Product_Record.objects.filter(id = record_id)
    record = record_list[0]
    return render_to_response('barcode/edit_header.html', {'record': record})

# record search page
def search(request):
    error_message = ""
    if request.method == 'POST': # If the form has been submitted...
        searchsum = request.POST.get('searchsum', '')
        record_list = Product_Record.objects.filter(checksum = searchsum)
        if record_list.count() == 0:
            error_message = "Record not found..."
        else:
            id = record_list[0].id
            return HttpResponseRedirect('/barcode/' + str(id) + '/detail/')

    return render_to_response('barcode/search.html', {'error_message': error_message, 'tab_search': True})
 
# record list page - this is also a form, for record deletions
def records(request):
    error_message = ''
    if request.method == 'POST': # If the form has been submitted...
        recordlist = request.POST.get('recordlist', '')
        if recordlist != '':
            records = recordlist.split(",")

            # delete all the selected records from the database
            for record in records:
                if record != '':
                    error_message = delete_record(record)

    latest_record_list = Product_Record.objects.order_by('-record_date')
    return render_to_response('barcode/records.html', {'latest_record_list': latest_record_list,
                                                       'error_message': error_message, 
                                                       'tab_records': True })

# input form - this is where the real work happens
def input(request):

    error_message = check_for_system_apps()
    foss_components = ''
    foss_versions = ''
    foss_copyrights = ''
    foss_attributions = ''
    foss_licenses = ''
    foss_license_urls = ''
    foss_urls = ''
    foss_spdxs = ''
    foss_patches = ''
    component_error = ''
    codetype = 'barcode'
    needs_setup = 0

    if request.method == 'POST': # If the form has been submitted...
        recordform = RecordForm(request.POST) # A form bound to the POST data      

        # barcode or qrcode?
        do_qr = request.POST.get('submit_qrcode', '')
        if do_qr != "":
            codetype = 'qrcode'
 
        # we need these whether it's valid or not to repopulate on a bad submit        
        foss_components = request.POST.get('foss_components', '')
        foss_versions = request.POST.get('foss_versions', '')
        foss_copyrights = request.POST.get('foss_copyrights', '')
        foss_attributions = request.POST.get('foss_attributions', '')
        foss_licenses = request.POST.get('foss_licenses', '')
        foss_license_urls = request.POST.get('foss_license_urls', '')
        foss_urls = request.POST.get('foss_urls', '')
        foss_spdxs = request.POST.get('foss_spdxs', '')

        # need at least one full component entry to proceed
        if foss_components == '' or foss_versions == '' or foss_copyrights == '' \
          or foss_attributions == '' or foss_licenses == '' or foss_license_urls == '' or foss_urls == '':
            component_error = "At least one full component record is required...<br>"
  
        # patches are each in their own text area
        if foss_components != '':
            components = foss_components.split(",")
            for i in range(0, len(components)-1):
                foss_patches += request.POST.get('foss_patches' + str(i), '') + ","

        # back to "normal" processing
        if recordform.is_valid() and component_error == '': # All validation rules pass
            recorddata = recordform.save(commit=False)       
            recorddata.save()
            recordid = recorddata.id
            data_dest = recorddata.file_path()
            if not recorddata.setup_directory():
                error_message += "Failed to create " + data_dest + "<br>"
            
            spdx_dest = os.path.join(data_dest, "spdx_files")
            patch_dest = os.path.join(data_dest, "patches")

            # if we have foss components, store them also, and the patches
            if foss_components != '':
                components = foss_components.split(",")
                versions = foss_versions.split(",")
                copyrights = foss_copyrights.split(",")
                attributions = foss_attributions.split(",")
                licenses = foss_licenses.split(",")
                license_urls = foss_license_urls.split(",")
                urls = foss_urls.split(",")
                spdxs = foss_spdxs.split(",")

                i = 0
                for foss in components:
                    if foss != "":
                        fossdata = FOSS_Components(brecord_id = recordid, 
                                                   package = foss, version = versions[i],
                                                   copyright = copyrights[i], attribution = attributions[i],
                                                   license = licenses[i], license_url = license_urls[i], 
                                                   url = urls[i], spdx_file = os.path.basename(spdxs[i]))
                        fossdata.save()
                        fossid = fossdata.id

                    # check for SPDX files and save in user_data
                    if spdxs[i] != '':
                        try:
                            recorddata.new_file_from_existing(spdxs[i],
                                                              "spdx_files")
                        except:
                            error_message += "Failed to copy " + str(spdxs[i]) + "to " + spdx_dest + "<br>"
                    
                    # check for patches and save in user_data
                    patch_files = request.POST.get('foss_patches' + str(i), '')
                    if patch_files != "":
                        patches = patch_files.split("\n")
                        for patch in patches:
                            patch = patch[:-1]
                            if patch != "":
                                patchdata = Patch_Files(frecord_id = fossid, path = os.path.basename(patch))
                                patchdata.save()
                                try:
                                    recorddata.new_file_from_existing(patch,
                                                                      "patches")
                                except:
                                    error_message += "Failed to copy " + str(patch) + "to " + patch_dest + "<br>"
                    i = i + 1

            # generate the checksum/barcode
            checksum = recorddata.calc_checksum()

            if checksum:
                recorddata.checksum = checksum
                recorddata.save()
                result = recorddata.checksum_to_barcode(codetype)
                if result:
                    error_message += "Barcode generation failed...<br>"
            else:
                error_message += "Checksum generation failed...<br>"

            if error_message == '':
                return HttpResponseRedirect('/barcode/' + str(recordid) + '/detail/')

    else:
        recordform = RecordForm() # An unbound form

        # check if the user has done basic setup
        settings_done = System_Settings.objects.filter(user_updated = True).count()
        if (settings_done) == 0:
            error_message = 'Please Configure Basic System Settings <a href="../sysconfig/">Here</a>'
            needs_setup = 1

    return render_to_response('barcode/input.html', {
                              'error_message': error_message, 'component_error': component_error, 
                              'recordform': recordform, 'needs_setup': needs_setup,
                              'foss_components': foss_components, 'foss_versions': foss_versions,
                              'foss_copyrights': foss_copyrights, 'foss_attributions': foss_attributions,
                              'foss_licenses': foss_licenses, 'foss_license_urls': foss_license_urls, 
                              'foss_urls': foss_urls, 'foss_spdxs': foss_spdxs,
                              'foss_patches': foss_patches, 'tab_input': True
    })

### these are all basically documentation support

# doc page
def documentation(request):
    from site_settings import gui_name, gui_version

    # Read the standalone docs, and reformat for the gui
    docs = ''
    status = 0

    try:
        f = open(settings.STATIC_DOC_ROOT + "/docs/index.html", 'r')

    except:
        # docs aren't created yet, try to do it
        status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && make")
        if status != 0:
            status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && ./text-docs-to-html > index.html.addons")
            if status == 0:
                status = os.system("cd " + settings.STATIC_DOC_ROOT + "/docs && cat index.html.base index.html.addons index.html.footer > index.html")
            else:
                docs = "<b>Error, no index.html in fossbarcode/media/docs.</b><br>"
                docs += "If working with a git checkout or tarball, please type 'make' in the top level directory.<br>"
                docs += "</body>"

    # something worked above
    if not docs:
        f = open(settings.STATIC_DOC_ROOT + "/docs/index.html", 'r')
        doc_index = []
        for line in f:
            #replace the div styles for embedded use
            line = line.replace('<div id="lside">', '<div id="lside_e">')
            line = line.replace('<div id="main">', '<div id="main_e">')
            line = line.replace('<img src="', '<img src="/site_media/docs/')
            doc_index.append(line)
        f.close()
    
        # drop the first 11 lines
        docs = ''.join(doc_index[11:])

    return render_to_response('barcode/documentation.html', 
                              {'name': gui_name, 
                               'version': gui_version, 
                               'gui_docs': docs })

# this does not have a corresponding dirlist.html
# this is dynamic filetree content fed to jqueryFileTree for the input.html file/dir selection
# script for jqueryFileTree points to /barcode/dirlist/
def dirlist(request):
    # filter out some directories that aren't useful from "/"
    not_wanted = [ '/proc', '/dev', '/sys', '/initrd' ]
    r=['<ul class="jqueryFileTree" style="display: none;">']
    try:
        d=urllib.unquote(request.POST.get('dir'))
        content = os.listdir(d)
        # slows things a little, but looks more like 'ls'
        for f in sorted(content, key=unicode.lower):
            ff=os.path.join(d,f)
            if ff not in not_wanted and f != 'lost+found':
                if os.path.isdir(ff): 
                    r.append('<li class="directory collapsed"><a href="#" rel="%s/">%s</a></li>' % (ff,f))
                else:
                    e=os.path.splitext(f)[1][1:] # get .ext and remove dot
                    r.append('<li class="file ext_%s"><a href="#" rel="%s">%s</a></li>' % (e,ff,f))
        r.append('</ul>')
    except Exception,e:
        r.append('Could not load directory: %s' % str(e))
    r.append('</ul>')
    return HttpResponse(''.join(r))

### utility functions

# check for the system utilities we need
# FIXME - what if "which" isn't present?
def check_for_system_apps():
    errmsg = ''
    apps_needed = ['barcode', 'qrencode' , 'pstopnm', 'pnmtopng', 'sam2p']
    for app in apps_needed:
        result = os.system("which " + app + "> /dev/null")
        if result:
            errmsg += "Could not find system app '<i>" + app + "</i>'...<br>"
            if app == "barcode" or app == "qrencode":
                errmsg += "(See the documentation for building '<i>" + app + "</i>' from source)<br>"

    if errmsg:
        errmsg += "Application will fail to generate qr/barcode images without these apps<br>"
        errmsg += "Please use your system package manager to install them<br>"

    return errmsg

# to remove a record
def delete_record(recid):
    errmsg = ''
    q = Product_Record.objects.filter(id = recid)
    checksum = q[0].checksum
    try:
        q[0].remove_directory()
    except:
        errmsg += "Failed to delete user data...<br>"
    q.delete()
    return errmsg

# delete table records requested by id from one of the input forms
def delete_records(table, rlist):
            
    records = rlist.split(",")

    for record in records:
        if record != '':
            q = table.objects.filter(id = record)
            q.delete()

# pre-render some of the record detail
def render_detail(id):
    media_root = '<a href="/site_media/user_data/'
    foss = []
    foss_list = FOSS_Components.objects.filter(brecord = id)
    for f in foss_list:
        fossid = f.id
        if f.spdx_file != '':
            spdx_file = media_root + str(id) + "/spdx_files/" + os.path.basename(f.spdx_file) + '">' + f.spdx_file + "</a><br>"
        else:
            spdx_file = ''

        patch_list = Patch_Files.objects.filter(frecord = fossid)
        patches = ""
        for p in patch_list:
            patches += media_root + str(id) + "/patches/" + os.path.basename(p.path) + '">' + p.path + "</a><br>"
        foss.append({'id': f.id, 'component': f.package, 'version': f.version, 
                     'copyright': f.copyright, 'attribution': f.attribution, 
                     'license': f.license, 'license_url': f.license_url, 
                     'url': f.url, 'spdx_file': spdx_file, 'patches': patches})
    return foss

