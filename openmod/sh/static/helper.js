function alertModal(message, header = "") {
    $('#alertModal').remove();
    $(document.body).append(
        '<div class="modal fade" id="alertModal" tabindex="-1" role="dialog" aria-labelledby="alertModalLabel" aria-hidden="true">' +
        '  <div class="modal-dialog" role="document">' +
        '    <div class="modal-content">' +
        '      <div class="modal-header">' +
        '        <h5 class="modal-title" id="alertModalLabel">' + header + '</h5>' +
        '        <button type="button" class="close" data-dismiss="modal" aria-label="Close">' +
        '          <span aria-hidden="true">&times;</span>' +
        '        </button>' +
        '      </div>' +
        '      <div class="modal-body">' +
        message +
        '      </div>' +
        '      <div class="modal-footer">' +
        '        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '</div>');
    $('#alertModal').modal();
}

function confirmModal(message, header = "", callback) {
    $('#confirmModal').remove();
    $(document.body).append(
        '<div class="modal fade" id="confirmModal" tabindex="-1" role="dialog" aria-labelledby="confirmModalLabel" aria-hidden="true">' +
        '  <div class="modal-dialog" role="document">' +
        '    <div class="modal-content">' +
        '      <div class="modal-header">' +
        '        <h5 class="modal-title" id="alertModalLabel">' + header + '</h5>' +
        '        <button type="button" class="close" data-dismiss="modal" aria-label="Close">' +
        '          <span aria-hidden="true">&times;</span>' +
        '        </button>' +
        '      </div>' +
        '      <div class="modal-body">' +
        message +
        '      </div>' +
        '      <div class="modal-footer">' +
        '        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>' +
        '        <button type="button" class="btn btn-primary confirm">Save changes</button>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '</div>');
    $('#confirmModal').modal().show();
    $('#confirmModal').on('hide.bs.modal', function(e) {
        callback(false);
    });
    $('#confirmModal .confirm').on('click', function(e) {
        $('#confirmModal').unbind( 'hide.bs.modal' );
        $('#confirmModal').modal('hide');
        callback(true);
    });
}

function promptModal(message, header = "", callback) {
    $('#promptModal').remove();
    $(document.body).append(
        '<div class="modal fade" id="promptModal" tabindex="-1" role="dialog" aria-labelledby="confirmModalLabel" aria-hidden="true">' +
        '  <div class="modal-dialog" role="document">' +
        '    <div class="modal-content">' +
        '      <div class="modal-header">' +
        '        <h5 class="modal-title" id="alertModalLabel">' + header + '</h5>' +
        '        <button type="button" class="close" data-dismiss="modal" aria-label="Close">' +
        '          <span aria-hidden="true">&times;</span>' +
        '        </button>' +
        '      </div>' +
        '      <div class="modal-body">' +
                    message +
            '      <div class="form-group">' +
            '          <input type="text" class="form-control" placeholder="' + message + '">' +
            '      </div>' +
        '      </div>' +
        '      <div class="modal-footer">' +
        '        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>' +
        '        <button type="button" class="btn btn-primary confirm">Save changes</button>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '</div>');
    $('#promptModal').modal().show();
    $('#promptModal').on('hide.bs.modal', function(e) {
        callback("");
    });
    $('#promptModal .confirm').on('click', function(e) {
        $('#promptModal').unbind( 'hide.bs.modal' );
        $('#promptModal').modal('hide');
        callback($('#promptModal').find('input').val());
    });
}