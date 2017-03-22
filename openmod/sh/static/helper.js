function alertModal(message, header = "", callback=function(){}) {
    $('#alertModal').remove();
    $(document.body).append(
        '<div class="modal fade" id="alertModal" tabindex="-1" role="dialog" aria-labelledby="alertModalLabel" aria-hidden="true">'
        +'<div class="modal-dialog" role="document">'
            +'<div class="modal-content">'
            +'<div class="modal-header">'
                +'<h5 class="modal-title" id="alertModalLabel">' + header + '</h5>'
                +'<button type="button" class="close" data-dismiss="modal" aria-label="Close">'
                +'<span aria-hidden="true">&times;</span>'
                +'</button>'
            +'</div>'
            +'<div class="modal-body">' + message + '</div>'
            +'<div class="modal-footer">'
                +'<button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>'
            +'</div>'
            +'</div>'
        +'</div>'
        +'</div>');
    $('#alertModal').modal().show();
    $('#alertModal').on('hide.bs.modal', function(e) {
        callback();
    });
}

function confirmModal(message, header = "", callback=function(){}) {
    $('#confirmModal').remove();
    $(document.body).append(
        '<div class="modal fade" id="confirmModal" tabindex="-1" role="dialog" aria-labelledby="conformModalLabel" aria-hidden="true">'
        +'<div class="modal-dialog" role="document">'
            +'<div class="modal-content">'
            +'<div class="modal-header">'
                +'<h5 class="modal-title" id="confirmModalLabel">' + header + '</h5>'
                +'<button type="button" class="close" data-dismiss="modal" aria-label="Close">'
                +'<span aria-hidden="true">&times;</span>'
                +'</button>'
            +'</div>'
            +'<div class="modal-body">' + message + '</div>'
            +'<div class="modal-footer">'
                +'<button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>'
                +'<button type="button" class="btn btn-secondary confirm" data-dismiss="modal">OK</button>'
            +'</div>'
            +'</div>'
        +'</div>'
        +'</div>');
    $('#confirmModal').modal().show();
    $('#confirmModal').on('hide.bs.modal', function(e) {
        callback(false);
    });
    $('#confirmModal .confirm').on('click', function(e) {
        $('#confirmModal').unbind( 'hide.bs.modal');
        $('#confirmModal').modal('hide');
        callback(true);
    });
}

function promptModal(text, defaultText="", header = "", callback=function(){}) {
    $('#promptModal').remove();
    $(document.body).append(
        '<div class="modal fade" id="promptModal" tabindex="-1" role="dialog" aria-labelledby="promptModalLabel" aria-hidden="true">'
        +'<div class="modal-dialog" role="document">'
            +'<div class="modal-content">'
            +'<div class="modal-header">'
                +'<h5 class="modal-title" id="promptModalLabel">' + header + '</h5>'
                +'<button type="button" class="close" data-dismiss="modal" aria-label="Close">'
                +'<span aria-hidden="true">&times;</span>'
                +'</button>'
            +'</div>'
            +'<div class="modal-body">' + text + '</div>'
                +'<div class="form-group">'
                    +'<input type="text" class="form-control" placeholder="' + defaultText + '">'
                +'</div>'
            +'<div class="modal-footer">'
                +'<button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>'
                +'<button type="button" class="btn btn-secondary confirm" data-dismiss="modal">OK</button>'
            +'</div>'
            +'</div>'
        +'</div>'
        +'</div>');
    $('#promptModal').modal().show();
    $('#promptModal').on('hide.bs.modal', function(e) {
        callback(null);
    });
    $('#promptModal .confirm').on('click', function(e) {
        $('#promptModal').unbind( 'hide.bs.modal');
        $('#promptModal').modal('hide');
        callback($('#promptModal').find('input').val());
    });
}
