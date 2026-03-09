// script.js

const programsByDept = {
    'ETEEAP': [
        'BS Business Administration – Marketing Management',
        'BS Business Administration – Operations Management',
        'BS Civil Engineering',
        'BS Computer Engineering',
        'BS Criminology',
        'BS Electrical Engineering',
        'BS Electronics Engineering',
        'BS Environmental Science',
        'BS Geodetic Engineering',
        'BS Hospitality Management',
        'BS Industrial Engineering',
        'BS Information Technology',
        'BS Mechanical Engineering',
        'BS Office Administration',
        'BS Public Administration',
        'BA Psychology',
        'BA Communication',
        'BSEd – English',
        'BSEd – Filipino',
        'BEEd',
        'Bachelor of Library and Information Science'
    ],
    'CNAHS': [
        'BS Nursing',
        'BS Medical Technology'
    ],
    'CAFA': [
        'Bachelor of Architecture',
        'Bachelor of Fine Arts – Visual Communication',
        'Bachelor of Multimedia Arts – Visual Design',
        'Bachelor of Multimedia Arts – Video Design',
        'Bachelor of Multimedia Arts – Game Design'
    ],
    'CAS': [
        'BA English Language',
        'BA Political Science',
        'BA Psychology',
        'BS Psychology',
        'BS Biology',
        'BS Economics',
        'BS Environmental Science',
        'Bachelor of Library and Information Science'
    ],
    'CIHTM': [
        'BS Hospitality Management – Cruise Management',
        'BS Hospitality Management – Culinary Arts',
        'BS Hospitality Management',
        'BS Tourism Management'
    ],
    'CCMS': [
        'BS Information Technology – Web & Mobile Application',
        'BS Information Technology – Cisco Networking',
        'BS Computer Science – Data Science',
        'BS Computer Science – Software Engineering',
        'BS Entertainment & Multimedia Computing – Game Development',
        'BS Entertainment & Multimedia Computing – Digital Animation Technology'
    ],
    'CME': [
        'BS Marine Engineering',
        'BS Marine Transportation'
    ],
    'CENG': [
        'BS Civil Engineering',
        'BS Mechanical Engineering',
        'BS Electrical Engineering',
        'BS Industrial Engineering',
        'BS Computer Engineering',
        'BS Electronics Engineering',
        'BS Geodetic Engineering'
    ],
    'CCJC': [
        'BS Criminology'
    ],
    'CED': [
        'Bachelor of Elementary Education',
        'Bachelor of Secondary Education – English',
        'Bachelor of Secondary Education – Filipino',
        'Bachelor of Secondary Education – Science',
        'Bachelor of Secondary Education – Mathematics',
        'Bachelor of Secondary Education – Social Studies',
        'Bachelor of Culture and Arts Education',
        'Bachelor of Physical Education',
        'Bachelor of Library and Information Science',
        'Bachelor of Elementary Education (ETEEAP)'
    ]
};

const documentPrices = {
    'Transcript_of_Records': 90,
    'Certification': 130
};
const stampPrice = 50;

function updatePrograms() {
    const deptSelect = document.getElementById('department');
    const progSelect = document.getElementById('program');

    if (!deptSelect || !progSelect) return;

    const dept = deptSelect.value;
    progSelect.innerHTML = '<option value="">-- Select Program --</option>';

    if (dept && programsByDept[dept]) {
        programsByDept[dept].forEach(prog => {
            const option = document.createElement('option');
            option.value = prog;
            option.textContent = prog;
            progSelect.appendChild(option);
        });
    }
}

function calculateTotal() {
    const totalEl = document.getElementById('total-amount');
    if (!totalEl) return;

    let total = 0;

    // Check specific documents
    for (const [key, price] of Object.entries(documentPrices)) {
        const input = document.getElementById(`qty_${key}`);
        if (input && input.value) {
            total += parseInt(input.value) * price;
        }
    }

    // Check stamp
    const stampInput = document.getElementById('stamp_qty');
    if (stampInput && stampInput.value) {
        total += parseInt(stampInput.value) * stampPrice;
    }

    totalEl.textContent = '₱' + total.toFixed(2);
}

document.addEventListener('DOMContentLoaded', () => {
    // Attach events
    const deptSelect = document.getElementById('department');
    if (deptSelect) {
        deptSelect.addEventListener('change', updatePrograms);
    }

    const qtyInputs = document.querySelectorAll('.qty-input');
    qtyInputs.forEach(input => {
        input.addEventListener('input', calculateTotal);
        input.addEventListener('change', calculateTotal);
    });

    // --- Confirmation Modal Logic ---
    const form = document.getElementById('request-form');
    const overlay = document.getElementById('confirm-overlay');
    const btnShow = document.getElementById('btn-show-confirm');
    const btnBack = document.getElementById('btn-go-back');
    const btnConfirm = document.getElementById('btn-confirm-submit');

    if (btnShow && form && overlay) {
        // Document labels keyed by input name
        const docLabels = {
            'qty_Copy_of_Grades': 'Copy of Grades',
            'qty_Transcript_of_Records': 'Transcript of Records',
            'qty_Honorable_Dismissal': 'Honorable Dismissal',
            'qty_Certification': 'Certification',
            'qty_Scholarship_(Off-Campus)': 'Scholarship (Off-Campus)',
            'qty_Request_for_F137A_/_SF10': 'Request for F137A / SF10',
            'stamp_qty': 'Documentary Stamp'
        };

        btnShow.addEventListener('click', () => {
            // Validate required fields first
            if (!form.reportValidity()) return;

            // Populate student info
            document.getElementById('confirm-name').textContent =
                form.querySelector('[name="full_name"]').value;
            document.getElementById('confirm-student-no').textContent =
                form.querySelector('[name="student_number"]').value;
            document.getElementById('confirm-dept').textContent =
                form.querySelector('[name="department"]').value;
            document.getElementById('confirm-program').textContent =
                form.querySelector('[name="program"]').value;

            // Build document list (only items with qty > 0)
            const docsList = document.getElementById('confirm-docs-list');
            docsList.innerHTML = '';
            let hasDoc = false;

            for (const [name, label] of Object.entries(docLabels)) {
                const input = form.querySelector(`[name="${name}"]`);
                const qty = input ? parseInt(input.value) || 0 : 0;
                if (qty > 0) {
                    hasDoc = true;
                    const li = document.createElement('li');
                    li.innerHTML = `<span>${label}</span><span class="doc-qty">x${qty}</span>`;
                    docsList.appendChild(li);
                }
            }

            if (!hasDoc) {
                const li = document.createElement('li');
                li.textContent = 'No documents selected.';
                li.style.color = '#999';
                li.style.fontStyle = 'italic';
                docsList.appendChild(li);
            }

            // Total
            document.getElementById('confirm-total-amount').textContent =
                document.getElementById('total-amount').textContent;

            // Show modal
            overlay.classList.add('active');
        });

        btnBack.addEventListener('click', () => {
            overlay.classList.remove('active');
        });

        btnConfirm.addEventListener('click', () => {
            form.submit();
        });

        // Close modal if clicking outside
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    }
});

// Admin AJAX functions
function markPaid(queueNumber) {
    fetch(`/cashier/pay/${queueNumber}`, {
        method: 'POST'
    }).then(res => res.json())
        .then(data => {
            if (data.success) {
                if (typeof fetchUpdates === 'function') fetchUpdates();
                else location.reload();
            }
        });
}

function serveQueue(queueNumber) {
    fetch(`/window21/serve/${queueNumber}`, {
        method: 'POST'
    }).then(res => res.json())
        .then(data => {
            if (data.success) {
                if (typeof fetchUpdates === 'function') fetchUpdates();
                else location.reload();
            }
        });
}

function completeQueue(queueNumber) {
    fetch(`/window21/complete/${queueNumber}`, {
        method: 'POST'
    }).then(res => res.json())
        .then(data => {
            if (data.success) {
                if (typeof fetchUpdates === 'function') fetchUpdates();
                else location.reload();
            }
        });
}
