let allUsers = [];
let filteredUsers = [];
let currentPage = 1;
let pageSize = 10;
let sortColumn = 'username';
let sortDirection = 'asc';
let searchQuery = '';

function getCookie(name){
    const m = document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : null;
}

async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users/', {
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load users');
        }
        
        const data = await response.json();
        allUsers = data.users;
        applyFiltersAndSort();
        renderUsersTable();
        updatePagination();
    } catch (error) {
        document.getElementById('users-table-body').innerHTML = 
            `<tr><td colspan="6" style="text-align:center;color:#ef4444;">Error loading users: ${error.message}</td></tr>`;
    }
}

function applyFiltersAndSort() {
    // Filter by search query
    if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        filteredUsers = allUsers.filter(user => {
            return (user.username || '').toLowerCase().includes(query) ||
                   (user.name || '').toLowerCase().includes(query) ||
                   (user.email || '').toLowerCase().includes(query) ||
                   (user.user_level || '').toLowerCase().includes(query);
        });
    } else {
        filteredUsers = [...allUsers];
    }
    
    // Sort
    filteredUsers.sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];
        
        // Handle null/undefined values
        if (aVal === null || aVal === undefined) aVal = '';
        if (bVal === null || bVal === undefined) bVal = '';
        
        // Convert to strings for comparison if needed
        if (sortColumn === 'date_joined') {
            aVal = new Date(aVal || 0);
            bVal = new Date(bVal || 0);
        } else if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = (bVal || '').toLowerCase();
        }
        
        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Reset to first page when filters change
    currentPage = 1;
}

function handleSearch() {
    searchQuery = document.getElementById('search-input').value;
    applyFiltersAndSort();
    renderUsersTable();
    updatePagination();
}

function handleSort(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    
    // Update sort indicators
    document.querySelectorAll('.users-table th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    const th = document.querySelector(`th[data-sort="${column}"]`);
    if (th) {
        th.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
    }
    
    applyFiltersAndSort();
    renderUsersTable();
    updatePagination();
}

function handlePageSizeChange() {
    pageSize = parseInt(document.getElementById('page-size').value);
    currentPage = 1;
    renderUsersTable();
    updatePagination();
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderUsersTable();
        updatePagination();
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredUsers.length / pageSize);
    if (currentPage < totalPages) {
        currentPage++;
        renderUsersTable();
        updatePagination();
    }
}

function goToPage(page) {
    currentPage = page;
    renderUsersTable();
    updatePagination();
}

function updatePagination() {
    const totalUsers = filteredUsers.length;
    const totalPages = Math.ceil(totalUsers / pageSize);
    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, totalUsers);
    
    // Update info texts
    document.getElementById('results-info').textContent = 
        `${totalUsers} user${totalUsers !== 1 ? 's' : ''} found`;
    document.getElementById('pagination-info').textContent = 
        `Showing ${totalUsers > 0 ? startIdx + 1 : 0}-${endIdx} of ${totalUsers} users`;
    
    // Update prev/next buttons
    document.getElementById('prev-btn').disabled = currentPage === 1;
    document.getElementById('next-btn').disabled = currentPage === totalPages || totalPages === 0;
    
    // Update page numbers
    const pageNumbersContainer = document.getElementById('page-numbers');
    pageNumbersContainer.innerHTML = '';
    
    if (totalPages <= 7) {
        // Show all pages
        for (let i = 1; i <= totalPages; i++) {
            pageNumbersContainer.appendChild(createPageButton(i));
        }
    } else {
        // Show first, last, and pages around current
        pageNumbersContainer.appendChild(createPageButton(1));
        
        if (currentPage > 3) {
            pageNumbersContainer.appendChild(createEllipsis());
        }
        
        for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
            pageNumbersContainer.appendChild(createPageButton(i));
        }
        
        if (currentPage < totalPages - 2) {
            pageNumbersContainer.appendChild(createEllipsis());
        }
        
        if (totalPages > 1) {
            pageNumbersContainer.appendChild(createPageButton(totalPages));
        }
    }
}

function createPageButton(page) {
    const btn = document.createElement('button');
    btn.className = 'page-btn' + (page === currentPage ? ' active' : '');
    btn.textContent = page;
    btn.onclick = () => goToPage(page);
    return btn;
}

function createEllipsis() {
    const span = document.createElement('span');
    span.textContent = '...';
    span.style.padding = '0.5rem';
    span.style.color = '#6b7280';
    return span;
}

function renderUsersTable() {
    const tbody = document.getElementById('users-table-body');
    
    if (filteredUsers.length === 0) {
        const message = searchQuery.trim() 
            ? 'No users match your search' 
            : 'No users found';
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#6b7280;">${message}</td></tr>`;
        return;
    }
    
    // Get paginated users
    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = startIdx + pageSize;
    const paginatedUsers = filteredUsers.slice(startIdx, endIdx);
    
    tbody.innerHTML = paginatedUsers.map(user => {
        const levelBadge = user.is_superuser 
            ? '<span class="badge badge-superuser">Superuser</span>' 
            : user.user_level === 'admin' 
                ? '<span class="badge badge-admin">Admin</span>' 
                : '<span class="badge badge-regular">Regular</span>';
        
        const streamBadge = user.allow_stream || user.user_level === 'admin' || user.is_superuser
            ? '<span class="badge badge-yes">Yes</span>'
            : '<span class="badge badge-no">No</span>';
        
        const dateJoined = user.date_joined ? new Date(user.date_joined).toLocaleDateString() : 'N/A';
        
        return `
            <tr>
                <td><a class="username-link" onclick="openEditModal(${user.id})">${user.username}</a></td>
                <td>${user.name || '-'}</td>
                <td>${user.email || '-'}</td>
                <td>${levelBadge}</td>
                <td>${streamBadge}</td>
                <td>${dateJoined}</td>
            </tr>
        `;
    }).join('');
}

function openCreateModal() {
    document.getElementById('create-modal').classList.add('active');
    document.getElementById('create-form').reset();
    document.getElementById('create-error').style.display = 'none';
}

function closeCreateModal() {
    document.getElementById('create-modal').classList.remove('active');
}

async function handleCreateUser(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    const data = {
        username: formData.get('username'),
        password: formData.get('password'),
        name: formData.get('name'),
        email: formData.get('email'),
        user_level: formData.get('user_level'),
        allow_stream: formData.get('allow_stream') === 'on'
    };
    
    try {
        const response = await fetch('/api/admin/users/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin',
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to create user');
        }
        
        closeCreateModal();
        loadUsers();
        showSuccessModal('User Created!', `User "${data.username}" has been created successfully.`);
    } catch (error) {
        document.getElementById('create-error').textContent = error.message;
        document.getElementById('create-error').style.display = 'block';
    }
}

function openEditModal(userId) {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;
    
    document.getElementById('edit-user-id').value = user.id;
    document.getElementById('edit-username').value = user.username;
    document.getElementById('edit-password').value = '';
    document.getElementById('edit-name').value = user.name || '';
    document.getElementById('edit-email').value = user.email || '';
    document.getElementById('edit-user-level').value = user.user_level;
    document.getElementById('edit-allow-stream').checked = user.allow_stream;
    document.getElementById('edit-error').style.display = 'none';
    
    // Show notes for superusers and admins
    if (user.is_superuser) {
        document.getElementById('edit-superuser-note').style.display = 'block';
        document.getElementById('edit-user-level').disabled = true;
    } else {
        document.getElementById('edit-superuser-note').style.display = 'none';
        document.getElementById('edit-user-level').disabled = false;
    }
    
    if (user.user_level === 'admin' || user.is_superuser) {
        document.getElementById('edit-stream-note').style.display = 'block';
        document.getElementById('edit-allow-stream').disabled = true;
        document.getElementById('edit-allow-stream').checked = true;
    } else {
        document.getElementById('edit-stream-note').style.display = 'none';
        document.getElementById('edit-allow-stream').disabled = false;
    }
    
    // Hide delete button if editing yourself or if admin trying to delete another admin (only superuser can)
    const deleteBtn = document.getElementById('btn-delete-user');
    const isSuperuser = window.USER_IS_SUPERUSER;
    
    if (user.username === window.CURRENT_USERNAME) {
        // Can't delete yourself
        deleteBtn.style.display = 'none';
    } else if (user.user_level === 'admin' && !isSuperuser) {
        // Only superuser can delete admin users
        deleteBtn.style.display = 'none';
    } else {
        deleteBtn.style.display = 'inline-flex';
    }
    
    document.getElementById('edit-modal').classList.add('active');
}

function closeEditModal() {
    document.getElementById('edit-modal').classList.remove('active');
}

async function handleEditUser(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const userId = formData.get('user_id');
    
    const data = {
        name: formData.get('name'),
        email: formData.get('email'),
        user_level: formData.get('user_level'),
        allow_stream: formData.get('allow_stream') === 'on'
    };
    
    // Only include password if provided
    const password = formData.get('password');
    if (password) {
        data.password = password;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/update/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin',
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to update user');
        }
        
        closeEditModal();
        loadUsers();
        const username = allUsers.find(u => u.id == userId)?.username || 'User';
        showSuccessModal('User Updated!', `User "${username}" has been updated successfully.`);
    } catch (error) {
        document.getElementById('edit-error').textContent = error.message;
        document.getElementById('edit-error').style.display = 'block';
    }
}

function showSuccessModal(title, message) {
    document.getElementById('success-modal-title').textContent = title;
    document.getElementById('success-modal-message').textContent = message;
    document.getElementById('success-modal').classList.add('active');
}

// Delete User Functions
let currentDeleteUserId = null;

function showDeleteUserModal() {
    const userId = document.getElementById('edit-user-id').value;
    const username = document.getElementById('edit-username').value;
    
    currentDeleteUserId = userId;
    document.getElementById('delete-user-name').textContent = username;
    document.getElementById('delete-user-modal-overlay').style.display = 'flex';
}

function closeDeleteUserModal() {
    currentDeleteUserId = null;
    document.getElementById('delete-user-modal-overlay').style.display = 'none';
}

async function confirmDeleteUser() {
    if (!currentDeleteUserId) return;
    
    const userId = currentDeleteUserId;
    const username = document.getElementById('edit-username').value;
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/delete/`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin'
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to delete user');
        }
        
        closeDeleteUserModal();
        closeEditModal();
        loadUsers();
        showSuccessModal('User Deleted!', `User "${username}" has been permanently deleted.`);
    } catch (error) {
        closeDeleteUserModal();
        document.getElementById('edit-error').textContent = error.message;
        document.getElementById('edit-error').style.display = 'block';
    }
}

// Click outside to close delete modal
document.addEventListener('click', (event) => {
    const overlay = document.getElementById('delete-user-modal-overlay');
    if (event.target === overlay) {
        closeDeleteUserModal();
    }
});

function closeSuccessModal() {
    document.getElementById('success-modal').classList.remove('active');
}

// Friends modal functions
window.addEventListener('toggleFriendsPanel', ()=>{
    openFriendsModal();
});

function openFriendsModal() {
    document.getElementById('friends-modal').classList.add('active');
    refreshFriendsRequests();
}

function closeFriendsModal() {
    document.getElementById('friends-modal').classList.remove('active');
    document.getElementById('friends-search-input').value = '';
    document.getElementById('friends-search-results').innerHTML = '';
}

async function refreshFriendsRequests() { 
    const r = await fetch('/api/friends/requests/', { credentials: 'same-origin' }); 
    if(!r.ok){ console.error('Requests fetch failed', r.status); return; } 
    const j = await r.json(); 
    const box = document.getElementById('friends-requests'); 
    box.innerHTML=''; 
    if(!(j.received?.length||j.sent?.length)){ 
        box.innerHTML='<div class="empty">No pending requests</div>'; 
        return; 
    } 
    (j.received||[]).forEach(u=>{ 
        const el=document.createElement('div'); 
        el.className='req'; 
        el.innerHTML=`<div>${u}</div><div><button class="btn btn-success" style="padding:0.35rem 0.75rem;" onclick="actFriendReq('accept','${u}')">Accept</button> <button class="btn btn-danger" style="padding:0.35rem 0.75rem;" onclick="actFriendReq('reject','${u}')">Reject</button></div>`; 
        box.appendChild(el); 
    }); 
    (j.sent||[]).forEach(u=>{ 
        const el=document.createElement('div'); 
        el.className='req'; 
        el.innerHTML=`<div>${u}<div class="muted" style="font-size:0.75rem;margin-top:0.15rem;">Request Sent</div></div><div><button class="btn btn-danger" style="padding:0.35rem 0.75rem;" onclick="undoFriendReq('${u}')">Undo Request</button></div>`; 
        box.appendChild(el); 
    }); 
}

async function actFriendReq(action, username){ 
    const ep = action==='accept' ? '/api/friends/accept/' : '/api/friends/reject/'; 
    await fetch(ep,{method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')}, body: JSON.stringify({ username })}); 
    refreshFriendsRequests(); 
}

async function doFriendSearch(q){ 
    const r=await fetch(`/api/users/search/?q=${encodeURIComponent(q)}`, { credentials: 'same-origin' }); 
    if(!r.ok){ console.error('Search fetch failed', r.status); return; } 
    const j=await r.json(); 
    const list=document.getElementById('friends-search-results'); 
    list.innerHTML=''; 
    if(!(j.results||[]).length){ 
        list.innerHTML='<div class="empty">No users found</div>'; 
        return; 
    } 
    j.results.forEach(it=>{ 
        const row=document.createElement('div'); 
        row.className='req'; 
        row.innerHTML=`<div>${it.username}${it.friendship_status === 'sent_pending' ? '<div class="muted" style="font-size:0.75rem;margin-top:0.15rem;">Request Sent</div>' : ''}</div><div>${renderFriendSearchActions(it)}</div>`; 
        list.appendChild(row); 
    }); 
}

function renderFriendSearchActions(it){ 
    if(it.friendship_status === 'sent_pending') return '<button class="btn btn-danger" style="padding:0.35rem 0.75rem;" onclick="undoFriendReq(\''+it.username+'\')">Undo Request</button>'; 
    if(it.friendship_status === 'sent_accepted' || it.friendship_status === 'received_accepted') return '<span class="muted" style="color:#10b981;font-weight:600;"><span style="font-size:1.1em;">✓</span> Already Friends</span>'; 
    if(it.friendship_status.startsWith('received_')) return `<button class="btn btn-success" style="padding:0.35rem 0.75rem;" onclick="actFriendReq('accept','${it.username}')">Accept</button> <button class="btn btn-danger" style="padding:0.35rem 0.75rem;" onclick="actFriendReq('reject','${it.username}')">Reject</button>`; 
    return `<button class="btn btn-primary" style="padding:0.35rem 0.75rem;" onclick="sendFriendReq('${it.username}')">Add</button>`; 
}

async function sendFriendReq(username){ 
    await fetch('/api/friends/request/',{method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')}, body: JSON.stringify({ username })}); 
    doFriendSearch(document.getElementById('friends-search-input').value || ''); 
    refreshFriendsRequests(); 
}

async function undoFriendReq(username){ 
    await fetch('/api/friends/undo/',{method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')}, body: JSON.stringify({ username })}); 
    const searchVal = document.getElementById('friends-search-input').value || '';
    if(searchVal) doFriendSearch(searchVal); 
    refreshFriendsRequests(); 
}

document.getElementById('friends-search-input').addEventListener('input', (e)=>{ 
    const q=e.target.value.trim(); 
    if(q.length<1){ 
        document.getElementById('friends-search-results').innerHTML=''; 
        return;
    } 
    doFriendSearch(q); 
});

// Load users on page load
loadUsers();
