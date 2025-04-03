// 将 showTab 函数定义在全局作用域
function showTab(tabId) {
    const tabs = ['basic-info', 'prize-settings', 'notification-settings'];
    tabs.forEach(tab => {
        document.getElementById(tab).classList.add('hidden');
    });
    document.getElementById(tabId).classList.remove('hidden');
}

// 封装模态框设置函数
function setupModal(modalId, openBtnId, closeBtnId) {
    const modal = document.getElementById(modalId);
    const openBtn = document.getElementById(openBtnId);
    const closeBtn = document.getElementById(closeBtnId);

    if (openBtn) {
        openBtn.addEventListener('click', () => {
            modal.classList.remove('hidden');
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }
}

// 封装 AJAX 请求函数
async function sendRequest(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {}
        };

        if (data) {
            options.body = data;
        }

        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('请求出错:', error);
        alert('网络错误，请稍后重试');
        return null;
    }
}

// 更新图片或视频链接可见性
function updateLinkVisibility(mediaTypeSelect, imageLinkContainer, videoLinkContainer) {
    const selectedValue = mediaTypeSelect.value;
    if (selectedValue === 'image') {
        imageLinkContainer.classList.remove('hidden');
        videoLinkContainer.classList.add('hidden');
    } else if (selectedValue === 'video') {
        videoLinkContainer.classList.remove('hidden');
        imageLinkContainer.classList.add('hidden');
    } else {
        imageLinkContainer.classList.add('hidden');
        videoLinkContainer.classList.add('hidden');
    }
}

// 加载群或频道列表
async function loadGroups() {
    // 这里应该替换为实际从后端获取群或频道列表数据的请求
    // 示例：const response = await sendRequest('/get_groups?lottery_id=1');
    const groups = [
        { id: 1, username: 'group1', name: 'Group 1' },
        { id: 2, username: 'group2', name: 'Group 2' }
    ];

    const tableBody = document.getElementById('group-table-body');
    tableBody.innerHTML = '';

    groups.forEach(group => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-4 py-2">${group.id}</td>
            <td class="px-4 py-2">${group.username}</td>
            <td class="px-4 py-2">${group.name}</td>
            <td class="px-4 py-2">
                <button data-group-id="${group.id}" class="bg-red-500 text-white px-2 py-1 rounded">删除</button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// 删除群或频道
async function deleteGroup(groupId) {
    if (confirm('是否删除该群或频道？')) {
        // 这里应该替换为实际从后端删除群或频道数据的请求
        // 示例：const response = await sendRequest(`/delete_group?group_id=${groupId}`, 'DELETE');
        // 重新加载群或频道列表
        await loadGroups();
    }
}

// 加载奖品列表
async function loadPrizes() {
    const response = await sendRequest('/get_prizes?lottery_id=1');
    if (response) {
        const tableBody = document.getElementById('prize-table-body');
        tableBody.innerHTML = '';
        response.prizes.forEach(prize => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-4 py-2">${prize.name}</td>
                <td class="px-4 py-2">${prize.total_count}</td>
                <td class="px-4 py-2">${prize.remaining_count}</td>
                <td class="px-4 py-2">
                    <button onclick="editPrize(${prize.id}, '${prize.name}', ${prize.total_count})" class="bg-yellow-500 text-white px-2 py-1 rounded">编辑</button>
                    <button onclick="deletePrize(${prize.id})" class="bg-red-500 text-white px-2 py-1 rounded">删除</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
}

// 删除奖品
async function deletePrize(prizeId) {
    if (confirm('是否删除该奖品？')) {
        const formData = new FormData();
        formData.append('prize_id', prizeId);
        const response = await sendRequest('/delete_prize', 'POST', formData);
        if (response && response.status === 'success') {
            await loadPrizes();
        }
    }
}

// 编辑奖品
function editPrize(prizeId, name, totalCount) {
    document.getElementById('edit-prize-id').value = prizeId;
    document.getElementById('edit-prize-name').value = name;
    document.getElementById('edit-prize-count').value = totalCount;
    document.getElementById('edit-prize-modal').classList.remove('hidden');
}

// 搜索参与用户
async function searchParticipants() {
    const status = document.getElementById('status-filter').value;
    const keyword = document.getElementById('keyword-filter').value;
    const response = await sendRequest(`/get_participants?lottery_id=1&status=${status}&keyword=${keyword}`);
    if (response) {
        const tableBody = document.getElementById('participants-table-body');
        tableBody.innerHTML = '';
        response.participants.forEach(participant => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-4 py-2">${participant.nickname}</td>
                <td class="px-4 py-2">${participant.user_id}</td>
                <td class="px-4 py-2">${participant.username}</td>
                <td class="px-4 py-2">${participant.status}</td>
                <td class="px-4 py-2">${participant.join_time}</td>
                <td class="px-4 py-2">操作</td>
            `;
            tableBody.appendChild(row);
        });
    }
}

// 创建抽奖
async function createLottery() {
    const description = document.getElementById('description');
    description.value = descriptionEditor.root.innerHTML;
    const formData = new FormData(document.getElementById('lottery-form'));
    const response = await sendRequest('/create_lottery', 'POST', formData);
    if (response && response.status === 'success') {
        alert('抽奖创建成功');
    }
}

// 添加奖品
async function addPrize() {
    const name = document.getElementById('prize-name').value;
    const totalCount = document.getElementById('prize-count').value;
    const formData = new FormData();
    formData.append('lottery_id', 1);
    formData.append('name', name);
    formData.append('total_count', totalCount);
    const response = await sendRequest('/add_prize', 'POST', formData);
    if (response && response.status === 'success') {
        document.getElementById('add-prize-modal').classList.add('hidden');
        await loadPrizes();
    }
}

// 编辑奖品保存
async function saveEditedPrize() {
    const prizeId = document.getElementById('edit-prize-id').value;
    const name = document.getElementById('edit-prize-name').value;
    const totalCount = document.getElementById('edit-prize-count').value;
    const formData = new FormData();
    formData.append('prize_id', prizeId);
    formData.append('name', name);
    formData.append('total_count', totalCount);
    const response = await sendRequest('/edit_prize', 'POST', formData);
    if (response && response.status === 'success') {
        document.getElementById('edit-prize-modal').classList.add('hidden');
        await loadPrizes();
        alert('奖品编辑成功');
    } else {
        alert('奖品编辑失败');
    }
}

// 保存通知设置
async function saveNotificationSettings() {
    const winnerPrivateNotice = document.getElementById('winner-private-notice');
    winnerPrivateNotice.value = winnerPrivateNoticeEditor.root.innerHTML;
    const creatorPrivateNotice = document.getElementById('creator-private-notice');
    creatorPrivateNotice.value = creatorPrivateNoticeEditor.root.innerHTML;
    const groupNotice = document.getElementById('group-notice');
    groupNotice.value = groupNoticeEditor.root.innerHTML;

    const formData = new FormData();
    formData.append('lottery_id', 1);
    formData.append('winner_private_notice', winnerPrivateNotice.value);
    formData.append('creator_private_notice', creatorPrivateNotice.value);
    formData.append('group_notice', groupNotice.value);

    const response = await sendRequest('/save_notification_settings', 'POST', formData);
    if (response && response.status === 'success') {
        alert('通知设置保存成功');
    } else {
        alert('通知设置保存失败');
    }
}

// 取消抽奖
async function cancelLottery() {
    if (confirm('你确定要取消本次抽奖吗？')) {
        const lotteryId = 1;
        const response = await sendRequest(`/cancel_lottery?lottery_id=${lotteryId}`);
        if (response && response.status === 'success') {
            alert('抽奖已成功取消');
        } else {
            alert('取消抽奖失败，请稍后重试');
        }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    // 设置模态框
    setupModal('participants-modal', 'participants-btn', 'close-participants-modal');
    setupModal('add-group-modal', 'add-group-btn', 'close-add-group-modal');
    setupModal('add-prize-modal', 'add-prize-btn', 'close-add-prize-modal');
    setupModal('edit-prize-modal', null, 'close-edit-prize-modal');

    // 搜索按钮事件
    document.getElementById('search-btn').addEventListener('click', searchParticipants);

    // 创建抽奖表单提交事件
    document.getElementById('lottery-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createLottery();
    });

    // 添加奖品确认按钮事件
    document.getElementById('confirm-add-prize').addEventListener('click', addPrize);

    // 媒体类型选择事件
    const mediaTypeSelect = document.getElementById('media-type');
    const imageLinkContainer = document.getElementById('image-link-container');
    const videoLinkContainer = document.getElementById('video-link-container');
    updateLinkVisibility(mediaTypeSelect, imageLinkContainer, videoLinkContainer);
    mediaTypeSelect.addEventListener('change', () => {
        updateLinkVisibility(mediaTypeSelect, imageLinkContainer, videoLinkContainer);
    });

    // 取消抽奖按钮事件
    document.getElementById('cancel-lottery-btn').addEventListener('click', cancelLottery);

    // 初始化加载群或频道列表
    await loadGroups();

    // 事件委托处理删除群或频道按钮点击事件
    document.getElementById('group-table-body').addEventListener('click', function (event) {
        if (event.target.tagName === 'BUTTON') {
            const groupId = parseInt(event.target.dataset.groupId);
            deleteGroup(groupId);
        }
    });

    // 编辑奖品取消按钮事件
    document.getElementById('cancel-edit-prize').addEventListener('click', () => {
        document.getElementById('edit-prize-modal').classList.add('hidden');
        document.getElementById('edit-prize-name').value = '';
        document.getElementById('edit-prize-count').value = '';
    });

    // 编辑奖品确认按钮事件
    document.getElementById('confirm-edit-prize').addEventListener('click', saveEditedPrize);

    // 保存通知设置按钮事件
    document.getElementById('save-notification-settings').addEventListener('click', saveNotificationSettings);

    // 取消添加群或频道按钮事件
    document.getElementById('cancel-add-group').addEventListener('click', () => {
        document.getElementById('add-group-modal').classList.add('hidden');
        document.getElementById('group-info').value = '';
    });

    // 初始化富文本编辑器
    const descriptionEditor = new Quill('#description-editor', {
        theme: 'snow'
    });
    const winnerPrivateNoticeEditor = new Quill('#winner-private-notice-editor', {
        theme: 'snow'
    });
    const creatorPrivateNoticeEditor = new Quill('#creator-private-notice-editor', {
        theme: 'snow'
    });
    const groupNoticeEditor = new Quill('#group-notice-editor', {
        theme: 'snow'
    });

    // 设置默认输入内容
    const defaultWinnerPrivateNotice = '{member}，恭喜您，参加抽奖活动{lotteryTitle}中奖了，奖品为{goodsName}，请联系创建人领取奖品。';
    const defaultCreatorPrivateNotice = '您的抽奖{lotteryTitle}（编号{lotterySn}）已成功开奖：\n中奖名单如下：\n{awardUserList}';
    const defaultGroupNotice = '抽奖{lotteryTitle}（编号{lotterySn}）已成功开奖：\n\n已参与人数：{joinNum}\n中奖名单如下：\n{awardUserList}';

    winnerPrivateNoticeEditor.root.innerHTML = defaultWinnerPrivateNotice;
    creatorPrivateNoticeEditor.root.innerHTML = defaultCreatorPrivateNotice;
    groupNoticeEditor.root.innerHTML = defaultGroupNotice;
});