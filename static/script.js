(function () {
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
        document.getElementById('close-add-group-modal').addEventListener('click', function () {
            closeModal('add-group-modal');
        });
        document.getElementById('add-prize-btn').addEventListener('click', function () {
            openModal('add-prize-modal');
        });
        document.getElementById('close-add-prize-modal').addEventListener('click', function () {
            closeModal('add-prize-modal');
        });
        document.getElementById('close-edit-prize-modal').addEventListener('click', function () {
            closeModal('edit-prize-modal');
        });
        document.getElementById('cancel-edit-prize').addEventListener('click', function () {
            closeModal('edit-prize-modal');
            document.getElementById('edit-prize-name').value = '';
            document.getElementById('edit-prize-count').value = '';
        });

        // 为“搜索”按钮添加点击事件监听器，点击该按钮时根据筛选条件获取参与者信息并更新表格
        document.getElementById('search-btn').addEventListener('click', function () {
            const status = document.getElementById('status-filter').value;
            const keyword = document.getElementById('keyword-filter').value;
            fetch(`/get_participants?lottery_id=1&status=${status}&keyword=${keyword}`)
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
                });
        });
        // 为抽奖表单添加提交事件监听器，提交表单时阻止默认提交行为，将富文本编辑器的内容赋值给隐藏输入框，然后发送请求到后端创建抽奖活动
        document.getElementById('lottery-form').addEventListener('submit', function (e) {
            e.preventDefault();
            const description = document.getElementById('description');
            description.value = descriptionEditor.root.innerHTML;
            const formData = new FormData(this);
            fetch('/create_lottery', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                    if (data.status === 'success') {
                        alert('抽奖创建成功');
                    }
                });
        });
        // 为“确认添加奖品”按钮添加点击事件监听器，点击该按钮时收集奖品信息，发送请求到后端添加奖品，添加成功后关闭模态框并重新加载奖品列表
        document.getElementById('confirm-add-prize').addEventListener('click', function () {
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
                        <button data-group-id="${group.id}" class="bg-red-500 text-white px-2 py-1 rounded">删除</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }

        // 事件委托处理删除按钮点击事件
        document.getElementById('group-table-body').addEventListener('click', function (event) {
            if (event.target.tagName === 'BUTTON') {
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
                            <td class="px-4 py-2">${prize.remaining_count}</td>
                            <td class="px-4 py-2">
                                <button onclick="editPrize(${prize.id}, '${prize.name}', ${prize.total_count})" class="bg-yellow-500 text-white px-2 py-1 rounded">编辑</button>
                                <button onclick="deletePrize(${prize.id})" class="bg-red-500 text-white px-2 py-1 rounded">删除</button>
                            </td>
                        `;
                        tableBody.appendChild(row);
                    });
                });
        }

        // 此函数用于删除奖品，点击删除按钮时，确认后发送请求到后端删除奖品，删除成功后重新加载奖品列表
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

        // 此函数用于编辑奖品，点击编辑按钮时，将奖品信息填充到编辑模态框中，并打开模态框
        function editPrize(prizeId, name, totalCount) {
            document.getElementById('edit-prize-id').value = prizeId;
            document.getElementById('edit-prize-name').value = name;
            document.getElementById('edit-prize-count').value = totalCount;
            openModal('edit-prize-modal');
        }
        // 为“确认编辑奖品”按钮添加点击事件监听器，点击该按钮时收集编辑后的奖品信息，发送请求到后端编辑奖品，编辑成功后关闭模态框并重新加载奖品列表
        document.getElementById('confirm-edit-prize').addEventListener('click', function () {
            const prizeId = document.getElementById('edit-prize-id').value;
            const name = document.getElementById('edit-prize-name').value;
            const totalCount = document.getElementById('edit-prize-count').value;
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

        document.getElementById('save-notification-settings').addEventListener('click', function () {
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

            fetch('/save_notification_settings', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                    if (data.status === 'success') {
                        alert('通知设置保存成功');
                    } else {
                        alert('通知设置保存失败');
                    }
                });
        });

        // 取消按钮功能
        document.getElementById('cancel-add-group').addEventListener('click', function () {
            closeModal('add-group-modal');
            document.getElementById('group-info').value = '';
        });

        // 确认按钮功能
        document.getElementById('confirm-add-group').addEventListener('click', function () {
            const groupInfo = document.getElementById('group-info').value;
            if (groupInfo) {
                // 这里可以添加保存群信息的逻辑
            }
        });

        // 渲染当前页的用户列表
        function renderUsers() {
            const startIndex = (currentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const currentUsers = users.slice(startIndex, endIndex);

            userList.innerHTML = '';
            currentUsers.forEach(user => {
                const listItem = document.createElement('li');
                listItem.textContent = user.name;
                userList.appendChild(listItem);
            });

            // 更新按钮状态
            prevPageButton.disabled = currentPage === 1;
            nextPageButton.disabled = currentPage === totalPages;
        }
    })
})();  