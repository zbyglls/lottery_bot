// 将 showTab 函数定义在全局作用域
function showTab(tabId) {
    const tabs = ['basic-info', 'prize-settings', 'notification-settings'];
    tabs.forEach(tab => {
        document.getElementById(tab).classList.add('hidden');
    });
    document.getElementById(tabId).classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    // 参与者模态框显示与隐藏
    document.getElementById('participants-btn').addEventListener('click', function () {
        document.getElementById('participants-modal').classList.remove('hidden');
    });
    document.getElementById('close-participants-modal').addEventListener('click', function () {
        document.getElementById('participants-modal').classList.add('hidden');
    });

    // 添加群或频道模态框显示与隐藏
    document.getElementById('add-group-btn').addEventListener('click', function () {
        document.getElementById('add-group-modal').classList.remove('hidden');
    });
    document.getElementById('close-add-group-modal').addEventListener('click', function () {
        document.getElementById('add-group-modal').classList.add('hidden');
    });

    // 搜索参与者
    document.getElementById('search-btn').addEventListener('click', function () {
        const status = document.getElementById('status-filter').value;
        const keyword = document.getElementById('keyword-filter').value;
        const lotteryId = 1; // 这里可根据实际情况动态获取
        fetch(`/get_participants?lottery_id=${lotteryId}&status=${status}&keyword=${keyword}`)
          .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
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
            })
          .catch(error => {
                console.error('获取参与者数据出错:', error);
                alert('获取参与者数据失败，请稍后重试');
            });
    });

    // 创建抽奖活动
    document.getElementById('lottery-form').addEventListener('submit', function (e) {
        e.preventDefault();
        const description = document.getElementById('description');
        description.value = descriptionEditor.root.innerHTML;
        const formData = new FormData(this);
        fetch('/create_lottery', {
            method: 'POST',
            body: formData
        })
          .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
          .then(data => {
                if (data.status === 'success') {
                    alert('抽奖创建成功');
                } else {
                    alert('抽奖创建失败，请稍后重试');
                }
            })
          .catch(error => {
                console.error('创建抽奖活动出错:', error);
                alert('创建抽奖活动失败，请稍后重试');
            });
    });

    // 添加奖品模态框显示与隐藏
    document.getElementById('add-prize-btn').addEventListener('click', function () {
        document.getElementById('add-prize-modal').classList.remove('hidden');
    });
    document.getElementById('close-add-prize-modal').addEventListener('click', function () {
        document.getElementById('add-prize-modal').classList.add('hidden');
    });

    // 确认添加奖品
    document.getElementById('confirm-add-prize').addEventListener('click', function () {
        const name = document.getElementById('prize-name').value;
        const totalCount = document.getElementById('prize-count').value;
        if (!name ||!totalCount) {
            alert('请输入奖品名称和数量');
            return;
        }
        const formData = new FormData();
        formData.append('lottery_id', 1); // 这里可根据实际情况动态获取
        formData.append('name', name);
        formData.append('total_count', totalCount);
        fetch('/add_prize', {
            method: 'POST',
            body: formData
        })
          .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
          .then(data => {
                if (data.status === 'success') {
                    document.getElementById('add-prize-modal').classList.add('hidden');
                    loadPrizes();
                } else {
                    alert('添加奖品失败，请稍后重试');
                }
            })
          .catch(error => {
                console.error('添加奖品出错:', error);
                alert('添加奖品失败，请稍后重试');
            });
    });

    // 媒体类型选择时更新链接可见性
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

    // 取消抽奖
    const cancelLotteryBtn = document.getElementById('cancel-lottery-btn');
    cancelLotteryBtn.addEventListener('click', () => {
        if (confirm('你确定要取消本次抽奖吗？')) {
            const lotteryId = 1; // 这里可根据实际情况动态获取
            fetch(`/cancel_lottery?lottery_id=${lotteryId}`, {
                method: 'GET'
            })
           .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
           .then(data => {
                if (data.status === 'success') {
                    alert('抽奖已成功取消');
                    // 可以在这里添加刷新页面或更新页面状态的代码
                    // location.reload(); 
                } else {
                    alert('取消抽奖失败，请稍后重试');
                }
            })
           .catch(error => {
                console.error('请求出错:', error);
                alert('网络错误，请稍后重试');
            });
        }
    });

    // 加载群或频道列表
    function loadGroups() {
        // 模拟从后端获取群或频道列表数据
        const groups = [
            { id: 1, username: 'group1', name: 'Group 1' },
            { id: 2, username: 'group2', name: 'Group 2' },
            // 可以添加更多群或频道数据
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

    // 事件委托处理删除群或频道按钮点击事件
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

    // 加载奖品列表
    function loadPrizes() {
        const lotteryId = 1; // 这里可根据实际情况动态获取
        fetch(`/get_prizes?lottery_id=${lotteryId}`)
          .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
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
            })
          .catch(error => {
                console.error('获取奖品数据出错:', error);
                alert('获取奖品数据失败，请稍后重试');
            });
    }

    // 删除奖品
    function deletePrize(prizeId) {
        if (confirm('是否删除该奖品？')) {
            const formData = new FormData();
            formData.append('prize_id', prizeId);
            fetch('/delete_prize', {
                method: 'POST',
                body: formData
            })
              .then(response => {
                    if (!response.ok) {
                        throw new Error('网络响应错误');
                    }
                    return response.json();
                })
              .then(data => {
                    if (data.status === 'success') {
                        loadPrizes();
                    } else {
                        alert('删除奖品失败，请稍后重试');
                    }
                })
              .catch(error => {
                    console.error('删除奖品出错:', error);
                    alert('删除奖品失败，请稍后重试');
                });
        }
    }

    // 编辑奖品模态框显示与填充数据
    function editPrize(prizeId, name, totalCount) {
        document.getElementById('edit-prize-id').value = prizeId;
        document.getElementById('edit-prize-name').value = name;
        document.getElementById('edit-prize-count').value = totalCount;
        document.getElementById('edit-prize-modal').classList.remove('hidden');
    }

    // 关闭编辑奖品模态框
    document.getElementById('close-edit-prize-modal').addEventListener('click', function () {
        document.getElementById('edit-prize-modal').classList.add('hidden');
    });

    // 取消编辑奖品
    document.getElementById('cancel-edit-prize').addEventListener('click', function () {
        document.getElementById('edit-prize-modal').classList.add('hidden');
        document.getElementById('edit-prize-name').value = '';
        document.getElementById('edit-prize-count').value = '';
    });

    // 确认编辑奖品
    document.getElementById('confirm-edit-prize').addEventListener('click', function () {
        const prizeId = document.getElementById('edit-prize-id').value;
        const name = document.getElementById('edit-prize-name').value;
        const totalCount = document.getElementById('edit-prize-count').value;
        if (!name ||!totalCount) {
            alert('请输入奖品名称和数量');
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
          .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
          .then(data => {
                if (data.status === 'success') {
                    document.getElementById('edit-prize-modal').classList.add('hidden');
                    loadPrizes();
                    alert('奖品编辑成功');
                } else {
                    alert('奖品编辑失败，请稍后重试');
                }
            })
          .catch(error => {
                console.error('编辑奖品出错:', error);
                alert('编辑奖品失败，请稍后重试');
            });
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

    // 保存通知设置
    document.getElementById('save-notification-settings').addEventListener('click', function () {
        const winnerPrivateNotice = document.getElementById('winner-private-notice');
        winnerPrivateNotice.value = winnerPrivateNoticeEditor.root.innerHTML;
        const creatorPrivateNotice = document.getElementById('creator-private-notice');
        creatorPrivateNotice.value = creatorPrivateNoticeEditor.root.innerHTML;
        const groupNotice = document.getElementById('group-notice');
        groupNotice.value = groupNoticeEditor.root.innerHTML;

        const formData = new FormData();
        formData.append('lottery_id', 1); // 这里可根据实际情况动态获取
        formData.append('winner_private_notice', winnerPrivateNotice.value);
        formData.append('creator_private_notice', creatorPrivateNotice.value);
        formData.append('group_notice', groupNotice.value);

        fetch('/save_notification_settings', {
            method: 'POST',
            body: formData
        })
          .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
          .then(data => {
                if (data.status === 'success') {
                    alert('通知设置保存成功');
                } else {
                    alert('通知设置保存失败，请稍后重试');
                }
            })
          .catch(error => {
                console.error('保存通知设置出错:', error);
                alert('保存通知设置失败，请稍后重试');
            });
    });

    // 取消添加群或频道
    document.getElementById('cancel-add-group').addEventListener('click', function () {
        document.getElementById('add-group-modal').classList.add('hidden');
        document.getElementById('group-info').value = '';
    });

    // 确认添加群或频道
    document.getElementById('confirm-add-group').addEventListener('click', function () {
        const groupInfo = document.getElementById('group-info').value;
        if (groupInfo) {
            // 这里可以添加保存群信息的逻辑
            alert('群信息保存成功');
            document.getElementById('add-group-modal').classList.add('hidden');
            document.getElementById('group-info').value = '';
            loadGroups();
        } else {
            alert('请输入群信息');
        }
    });

    // 初始化加载群或频道列表和奖品列表
    loadGroups();
    loadPrizes();
});