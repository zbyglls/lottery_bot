document.addEventListener('DOMContentLoaded', function() {
    const participantsBtn = document.getElementById('participants-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const modal = document.getElementById('participants-modal');
    const closeModal = document.getElementById('close-modal');
    const searchBtn = document.getElementById('search-btn');
    const lotteryId = document.getElementById('lottery_id').value; // 获取抽奖ID 
    // 参与者列表
    participantsBtn.addEventListener('click', function() {
        modal.classList.add('show');
        loadParticipants();
    });

    closeModal.addEventListener('click', function() {
        modal.classList.remove('show');
    });

    // 取消抽奖
    cancelBtn.addEventListener('click', async function() {
        if (confirm('确定要取消此次抽奖吗？')) {
            try {// 获取抽奖ID
                const response = await fetch(`/cancel_lottery?lottery_id=${lotteryId}`);
                const data = await response.json();
                if (data.status === 'success') {
                    alert('抽奖已取消');
                    window.location.reload();
                } else {
                    alert(data.message || '取消失败');
                }
            } catch (error) {
                alert('操作失败，请稍后重试');
            }
        }
    });
    // 每页显示的记录数
    const itemsPerPage = 10;
    // 当前页码
    let currentPage = 1;
    // 加载参与者列表
    async function loadParticipants(page = 1) {
        try {
            const keyword = document.getElementById('search-input').value;
            const response = await fetch(`/get_participants?lottery_id=${lotteryId}&keyword=${keyword}&page=${page}`);
            const data = await response.json();
            
            // 获取容器元素，如果不存在则提前返回
            const statsContainer = document.getElementById('participants-stats');
            const tbody = document.getElementById('participants-list');
            if (!statsContainer || !tbody) {
                console.error('未找到必要的 DOM 元素');
                return;
            }

            // 更新统计信息
            const totalParticipants = data.participants.length || 0;
            statsContainer.innerHTML = `
                <div class="bg-blue-50 p-3 mb-4 rounded-lg shadow-sm">
                    <p class="text-center text-gray-600">总参与人数</p>
                    <p class="text-center text-2xl font-bold text-blue-600">${totalParticipants}</p>
                </div>
            `;

            // 清空并更新表格内容
            tbody.innerHTML = '';
            
            if (data.participants && data.participants.length > 0) {
                data.participants.forEach(p => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="px-4 py-2">${p.nickname || '-'}</td>
                        <td class="px-4 py-2">${p.username}</td>
                        <td class="px-4 py-2">${p.user_id}</td>
                        <td class="px-4 py-2">${p.join_time}</td>
                    `;
                    tbody.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td colspan="4" class="px-4 py-2 text-center text-gray-500">暂无参与者</td>
                `;
                tbody.appendChild(row);
            }

            // 更新分页信息
            const totalPages = Math.ceil(totalParticipants / itemsPerPage);
            const paginationInfo = document.getElementById('pagination-info');
            if (paginationInfo) {
                paginationInfo.textContent = `第 ${page} 页，共 ${totalPages} 页`;
            }

            // 更新分页按钮状态
            const prevPageBtn = document.getElementById('prev-page');
            const nextPageBtn = document.getElementById('next-page');
            if (prevPageBtn && nextPageBtn) {
                prevPageBtn.disabled = page <= 1;
                nextPageBtn.disabled = page >= totalPages;
            }

        } catch (error) {
            console.error('加载参与者失败:', error);
            // 显示错误提示
            const statsContainer = document.getElementById('participants-stats');
            if (statsContainer) {
                statsContainer.innerHTML = `
                    <div class="bg-red-50 p-3 mb-4 rounded-lg shadow-sm">
                        <p class="text-center text-red-600">加载参与者信息失败，请稍后重试</p>
                    </div>
                `;
            }
        }
    }

    // 搜索功能
    searchBtn.addEventListener('click', function() {
        currentPage = 1; // 搜索时重置为第一页
        loadParticipants(1); // 从第一页开始加载
    });

    // 添加分页按钮事件处理
    document.getElementById('prev-page').addEventListener('click', function() {
        if (currentPage > 1) {
            currentPage--;
            loadParticipants(currentPage);
        }
    });

    document.getElementById('next-page').addEventListener('click', function() {
        currentPage++;
        loadParticipants(currentPage);
    });

    // 添加搜索框回车事件
    document.getElementById('search-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            currentPage = 1;
            loadParticipants(1);
        }
    });
});