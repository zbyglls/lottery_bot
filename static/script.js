// 此函数用于切换显示不同的选项卡
function showTab(tabId) {
    const tabs = ['basic-info', 'prize-settings', 'notification-settings'];
    tabs.forEach(tab => {
        document.getElementById(tab).classList.add('hidden');
    });
    document.getElementById(tabId).classList.remove('hidden');
}
// 当文档的 DOM 内容加载完成后执行以下代码
document.addEventListener('DOMContentLoaded', () => {
    // 通用的打开模态框函数
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('show');
        setTimeout(() => {
            modal.classList.add('fade-in');
        }, 50);
    }
    // 通用的关闭模态框函数
    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('fade-in');
        setTimeout(() => {
            modal.classList.remove('show');
        }, 300);
    }

    document.getElementById('participants-btn').addEventListener('click', function () {
        openModal('participants-modal');
    });
    document.getElementById('close-participants-modal').addEventListener('click', function () {
        closeModal('participants-modal');
    });
    document.getElementById('add-group-btn').addEventListener('click', function () {
        openModal('add-group-modal');
    });
    document.getElementById('close-add-group-modal').addEventListener('click', function (event) {
        event.stopPropagation(); // 阻止事件冒泡
        closeModal('add-group-modal');
        document.getElementById('group-info').value = '';
    });
    document.getElementById('cancel-add-group').addEventListener('click', function (event) {
        event.stopPropagation(); // 阻止事件冒泡
        closeModal('add-group-modal');
        document.getElementById('group-info').value = '';
    });
    document.getElementById('confirm-add-group').addEventListener('click', function (event) {
        event.stopPropagation(); // 阻止事件冒泡
        // 这里可以添加确认添加群组的逻辑
        const groupInfo = document.getElementById('group-info').value;
        if (groupInfo) {
            // 发送请求到后端保存群信息
            const formData = new FormData();
            formData.append('group_info', groupInfo);
            fetch('/save_group_info', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 保存成功，重新加载群或频道列表
                    loadGroups();
                } else {
                    alert(data.message);
                }
            });
        }
        closeModal('add-group-modal');
    });
    document.getElementById('add-prize-btn').addEventListener('click', function () {
        openModal('add-prize-modal');
    });
    document.getElementById('close-add-prize-modal').addEventListener('click', function () {
        closeModal('add-prize-modal');
    });
    document.getElementById('cancel-add-prize').addEventListener('click', function () {
        closeModal('add-prize-modal');
        document.getElementById('edit-prize-name').value = '';
        document.getElementById('edit-prize-count').value = '';
    });
    document.getElementById('close-edit-prize-modal').addEventListener('click', function () {
        closeModal('edit-prize-modal');
    });
    document.getElementById('cancel-edit-prize').addEventListener('click', function () {
        closeModal('edit-prize-modal');
        document.getElementById('edit-prize-name').value = '';
        document.getElementById('edit-prize-count').value = '';
    });

    

    // 监听表单提交事件
    document.getElementById('lottery-form').addEventListener('submit', async function (event) {
        event.preventDefault(); // 首先阻止表单默认提交
        if (!validateForm()) {
            console.log('表单验证失败，终止提交');
            return false;
        }
        // 验证通过后再执行创建抽奖
        try {
            const formData = new FormData(this);

            // 同步抽奖文字说明编辑器内容到隐藏输入框
            const description = descriptionEditor.root.innerHTML;
            document.getElementById('description').value = description;

            // 获取奖品信息
            const prizeTableBody = document.getElementById('prize-table-body');
            const rows = prizeTableBody.getElementsByTagName('tr');
            for (let i = 0; i < rows.length; i++) {
                const cells = rows[i].getElementsByTagName('td');
                const prizeName = cells[0].textContent;
                const prizeCount = cells[1].textContent;
                formData.append('prize_name', prizeName);
                formData.append('prize_count', prizeCount);
            }

            // 获取通知设置信息
            const winnerPrivateNotice = document.getElementById('winner-private-notice').value;
            const creatorPrivateNotice = document.getElementById('creator-private-notice').value;
            const groupNotice = document.getElementById('group-notice').value;
            formData.append('winner_private_notice', winnerPrivateNotice);
            formData.append('creator_private_notice', creatorPrivateNotice);
            formData.append('group_notice', groupNotice);

            // 提交表单数据
            const response = await fetch('/create_lottery', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (result.status === 'success') {
                alert('抽奖创建成功');
                // window.location.href = '/lottery_list';
            } else {
                alert('抽奖创建失败：' + result.message);
            }
        } catch (error) {
            console.error('创建抽奖出错:', error);
            alert('创建抽奖时发生错误');
        }
    });

    // 确认添加奖品
    document.getElementById('confirm-add-prize').addEventListener('click', function () {
        if (validateAddPrize()) {
            const name = document.getElementById('prize-name').value;
            const totalCount = document.getElementById('prize-count').value;
            const formData = new FormData();
            formData.append('lottery_id', 1);
            formData.append('name', name);
            formData.append('total_count', totalCount);
            fetch('/add_prize', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                    if (data.status === 'success') {
                        closeModal('add-prize-modal');
                        loadPrizes();
                    }
                });
        }
    });
    // 此函数用于加载奖品列表，发送请求到后端获取奖品信息，并将其显示在表格中
    function loadPrizes() {
        fetch('/get_prizes?lottery_id=1')
        .then(response => response.json())
        .then(data => {
                const tableBody = document.getElementById('prize-table-body');
                tableBody.innerHTML = '';
                data.prizes.forEach(prize => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="px-4 py-2">${prize.name}</td>
                        <td class="px-4 py-2">${prize.total_count}</td>
                        <td class="px-4 py-2">
                            <button onclick="editPrize(${prize.id}, '${prize.name}', ${prize.total_count})" class="bg-yellow-500 text-white px-2 py-1 rounded">编辑</button>
                            <button onclick="deletePrize(${prize.id})" class="bg-red-500 text-white px-2 py-1 rounded">删除</button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            });
    }

    // 删除奖品，点击删除按钮时，确认后发送请求到后端删除奖品，删除成功后重新加载奖品列表
    function deletePrize(prizeId) {
        if (confirm('是否删除该奖品？')) {
            const formData = new FormData();
            formData.append('prize_id', prizeId);
            fetch('/delete_prize', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                    if (data.status === 'success') {
                        loadPrizes();
                    }
                });
        }
    }
    window.deletePrize = deletePrize;

    // 编辑奖品，点击编辑按钮时，将奖品信息填充到编辑模态框中，并打开模态框
    function editPrize(prizeId, name, totalCount) {
            document.getElementById('edit-prize-id').value = prizeId;
            document.getElementById('edit-prize-name').value = name;
            document.getElementById('edit-prize-count').value = totalCount;
            openModal('edit-prize-modal');
        
    }
    window.editPrize = editPrize;
    // 确认编辑奖品”按钮，点击该按钮时收集编辑后的奖品信息，发送请求到后端编辑奖品，编辑成功后关闭模态框并重新加载奖品列表
    document.getElementById('confirm-edit-prize').addEventListener('click', function () {
        const prizeId = document.getElementById('edit-prize-id').value;
        const name = document.getElementById('edit-prize-name').value;
        const totalCount = document.getElementById('edit-prize-count').value;
         // 添加验证
        if (!validatePrize(name, totalCount)) {
            return;
        }
        const formData = new FormData();
        formData.append('prize_id', prizeId);
        formData.append('name', name);
        formData.append('total_count', totalCount);
        fetch('/edit_prize', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
                if (data.status === 'success') {
                    closeModal('edit-prize-modal');
                    loadPrizes();
                    alert('奖品编辑成功');
                } else {
                    alert('奖品编辑失败');
                }
            });
    });

    const mediaTypeSelect = document.getElementById('media-type');
    const imageLinkContainer = document.getElementById('image-link-container');
    const videoLinkContainer = document.getElementById('video-link-container');

    function updateLinkVisibility() {
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

    updateLinkVisibility();
    mediaTypeSelect.addEventListener('change', updateLinkVisibility);

    // 获取取消抽奖按钮
    const cancelLotteryBtn = document.getElementById('cancel-lottery-btn');

    // 为取消抽奖按钮添加点击事件监听器
    cancelLotteryBtn.addEventListener('click', () => {
        // 弹出确认框，让用户确认是否取消抽奖
        if (confirm('你确定要取消本次抽奖吗？')) {
            // 模拟抽奖 ID，实际应用中应从页面或数据中获取
            const lotteryId = 1; 

            // 发送请求到后端取消抽奖
            fetch(`/cancel_lottery?lottery_id=${lotteryId}`, {
                method: 'GET'
            })
        .then(response => response.json())
        .then(data => {
                if (data.status === 'success') {
                    // 取消成功，给出提示并进行相应操作，如刷新页面
                    alert('抽奖已成功取消');
                    // 可以在这里添加刷新页面或更新页面状态的代码
                    // location.reload(); 
                } else {
                    // 取消失败，给出提示
                    alert('取消抽奖失败，请稍后重试');
                }
            })
        .catch(error => {
                console.error('请求出错:', error);
                alert('网络错误，请稍后重试');
            });
        }
    });

    // 获取参与方式的单选按钮和相关的容器元素
    const privateChatRadio = document.getElementById('private-chat');
    const groupKeywordRadio = document.getElementById('group-keyword');
    const groupKeywordFields = document.getElementById('group-keyword-fields');

    // 监听参与方式的选择变化
    function handleJoinMethodChange() {
        if (privateChatRadio.checked) {
            groupKeywordFields.classList.add('hidden');
        } else if (groupKeywordRadio.checked) {
            groupKeywordFields.classList.remove('hidden');
            // 加载关键词群组列表
            loadKeywordGroups();
        }
    }

    // 初始化时调用一次，确保初始状态正确
    handleJoinMethodChange();

    // 为单选按钮添加事件监听器
    privateChatRadio.addEventListener('change', handleJoinMethodChange);
    groupKeywordRadio.addEventListener('change', handleJoinMethodChange);

    // 加载关键词群组列表
    function loadKeywordGroups() {
        fetch('/get_keyword_groups')
        .then(response => response.json())
        .then(data => {
                const keywordGroupSelect = document.getElementById('keyword-group');
                keywordGroupSelect.innerHTML = '';
                data.groups.forEach(group => {
                    const option = document.createElement('option');
                    option.value = group.id;
                    option.textContent = group.name;
                    keywordGroupSelect.appendChild(option);
                });
            });
    }

    // 初始化加载群或频道列表
    loadGroups();

    // 加载群或频道列表
    function loadGroups() {
        // 模拟从后端获取群或频道列表数据
        const groups = [
            { id: 1, username: 'group1', name: 'Group 1' },
            { id: 2, username: 'group2', name: 'Group 2' },
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
                    <button data-group-id="${group.id}" class="bg-red-500 text-white px-2 py-1 rounded" type="button">删除</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
    // 事件委托处理删除按钮点击事件
    document.getElementById('group-table-body').addEventListener('click', function (event) {
        if (event.target.tagName === 'BUTTON') {
            event.stopPropagation(); // 阻止事件冒泡
            const groupId = parseInt(event.target.dataset.groupId);
            if (confirm('是否删除该群或频道？')) {
                // 模拟从后端删除群或频道数据
                // 实际应用中需要发送请求到后端进行删除操作
                const groups = JSON.parse(localStorage.getItem('groups')) || [];
                const newGroups = groups.filter(group => group.id !== groupId);
                localStorage.setItem('groups', JSON.stringify(newGroups));

                // 重新加载群或频道列表
                loadGroups();
            }
        }
    });

    // 获取开奖方式的单选按钮和相关的容器元素
    const fullParticipantsRadio = document.getElementById('full-participants');
    const timedDrawRadio = document.getElementById('timed-draw');
    const participantCountContainer = document.getElementById('participant-count-container');
    const drawDateContainer = document.getElementById('draw-date-container');

    // 监听开奖方式的选择变化
    function handleDrawMethodChange() {
        if (fullParticipantsRadio.checked) {
            participantCountContainer.classList.remove('hidden');
            drawDateContainer.classList.add('hidden');
        } else if (timedDrawRadio.checked) {
            participantCountContainer.classList.add('hidden');
            drawDateContainer.classList.remove('hidden');
        }
    }

    // 初始化时调用一次，确保初始状态正确
    handleDrawMethodChange();

    // 为单选按钮添加事件监听器
    fullParticipantsRadio.addEventListener('change', handleDrawMethodChange);
    timedDrawRadio.addEventListener('change', handleDrawMethodChange);





    // 初始化抽奖文字说明编辑器
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


    // 每页显示的记录数
    const itemsPerPage = 10;
    // 当前页码
    let currentPage = 1;
    // 加载参与者信息
    function loadParticipants(page = 1) {
        const status = document.getElementById('status-filter').value;
        const keyword = document.getElementById('keyword-filter').value;
        fetch(`/get_participants?lottery_id=1&status=${status}&keyword=${keyword}&page=${page}&limit=${itemsPerPage}`)
          .then(response => response.json())
          .then(data => {
                const tableBody = document.getElementById('participants-table-body');
                tableBody.innerHTML = '';
                data.participants.forEach(participant => {
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

                // 更新分页按钮
                updatePagination(data.totalPages, page);
            });
    }
    // 更新分页按钮
    function updatePagination(totalPages, currentPage) {
        const pagination = document.getElementById('participants-pagination');
        if (pagination) {
            pagination.innerHTML = '';
            for (let i = 1; i <= totalPages; i++) {
                const button = document.createElement('button');
                button.textContent = i;
                button.classList.add('bg-blue-500', 'text-white', 'px-2', 'py-1', 'rounded', 'm-1');
                if (i === currentPage) {
                    button.disabled = true;
                }
                button.addEventListener('click', () => {
                    loadParticipants(i);
                });
                pagination.appendChild(button);
            }
        }
    }
    // 为“搜索”按钮添加点击事件监听器，点击该按钮时根据筛选条件获取参与者信息并更新表格
    document.getElementById('search-btn').addEventListener('click', function () {
        currentPage = 1;
        loadParticipants(currentPage);
    });
    // 初始化加载参与者信息
    loadParticipants(currentPage);
});
