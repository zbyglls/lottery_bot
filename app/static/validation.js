// validation.js
function validateForm(event) {
    // 抽奖标题验证
    const title = document.getElementById('title').value;
    if (!title) {
        alert('请输入抽奖标题！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }


    // 图片或视频链接输入框验证
    const mediaType = document.getElementById('media-type').value;
    let link = '';
    if (mediaType === 'image') {
        link = document.getElementById('image-link').value;
    } else if (mediaType === 'video') {
        link = document.getElementById('video-link').value;
    }
    if ((mediaType === 'image' || mediaType === 'video') && !link) {
        alert('请输入图片或视频链接！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }

    // 抽奖文字说明验证
    const descriptionEditor = new Quill('#description-editor');
    const description = descriptionEditor.root.innerHTML;
    if (!description || description === '<p><br></p>') {
        alert('请输入抽奖文字说明！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }

    // 请选关键词群组选择框验证
    const joinMethod = document.querySelector('input[name="join_method"]:checked').value;
    if (joinMethod === 'send_keywords_in_group') {
        const keywordGroup = document.getElementById('keyword-group-search').value;
        if (!keywordGroup) {
            alert('请选择关键词群组！');
            if (event) {
                event.preventDefault();
                event.stopPropagation(); // 阻止事件冒泡
            }
            return false;
        }
        // 抽奖关键词输入框验证
        const lotteryKeyword = document.getElementById('lottery-keyword').value;
        if (!lotteryKeyword) {
            alert('请输入抽奖关键词！');
            if (event) {
                event.preventDefault();
                event.stopPropagation(); // 阻止事件冒泡
            }
            return false;
        }
    }
    if (joinMethod === 'private_chat_bot') {
        // 需要成员加入的群或频道列表验证
        const groupTableBody = document.getElementById('group-table-body');
        const groupRows = groupTableBody.getElementsByTagName('tr');
        if (groupRows.length === 0) {
            alert('请添加需要成员加入的群或频道！');
            if (event) {
                event.preventDefault();
                event.stopPropagation(); // 阻止事件冒泡
            }
            return false;
        }
    }

    // 验证群组发言设置
    if (joinMethod === 'send_messages_in_group') {
        // 验证是否选择了群组
        const messageGroup = document.getElementById('message-group-search').value;
        if (!messageGroup) {
            alert('请选择发言群组！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return false;
        }

        // 验证发言条数和时间范围
        const messageCount = parseInt(document.getElementById('message-count').value);
        const checkTime = parseInt(document.getElementById('message-check-time').value);
        
        if (!validateMessageSettings(messageCount, checkTime)) {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return false;
        }
    }

    // 根据开奖方式进行验证
    const drawMethod = document.querySelector('input[name="draw_method"]:checked').value;
    if (drawMethod === 'draw_when_full') {
        // 满人开奖时验证参与人数
        const participantCount = document.getElementById('participant-count').value;
        if (!participantCount || isNaN(participantCount) || parseInt(participantCount) <= 0) {
            alert('参与人数必须大于 0！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return false;
        }
    } else if (drawMethod === 'draw_at_time') {
        // 定时开奖时验证开奖日期
        const drawDate = document.getElementById('draw-date').value;
        if (!drawDate) {
            alert('请选择开奖日期！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return false;
        }
        const now = new Date();
        const selectedDate = new Date(drawDate);
        if (selectedDate <= now) {
            alert('开奖日期不能选择过去的时间！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return false;
        }
    }

    // 奖品列表验证
    const prizeTableBody = document.getElementById('prize-table-body');
    const prizeRows = prizeTableBody.getElementsByTagName('tr');
    if (prizeRows.length === 0) {
        alert('请设置奖品！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }
    return true;
}

// 添加判断奖品是否重复的函数
function isPrizeDuplicate(prizeName) {
    const prizeTableBody = document.getElementById('prize-table-body');
    const prizeRows = prizeTableBody.getElementsByTagName('tr');
    
    for (let i = 0; i < prizeRows.length; i++) {
        const existingPrizeName = prizeRows[i].getElementsByTagName('td')[0].textContent.trim();
        if (existingPrizeName === prizeName) {
            return true;
        }
    }
    return false;
}

// 修改 validateAddPrize 函数
function validateAddPrize() {
    // 奖品名称输入框验证
    const prizeName = document.getElementById('prize-name').value.trim();
    if (!prizeName) {
        alert('请输入奖品名称！');
        return false;
    }

    // 检查奖品名称是否重复
    if (isPrizeDuplicate(prizeName)) {
        alert('该奖品已存在，请勿重复添加！');
        return false;
    }

    // 奖品数量输入框验证
    const prizeCount = document.getElementById('prize-count').value;
    if (!prizeCount || isNaN(prizeCount) || parseInt(prizeCount) <= 0) {
        alert('奖品数量必须大于 0！');
        return false;
    }

    return true;
}

// 修改 validatePrize 函数，用于编辑奖品时的验证
function validatePrize(name, count, originalName) {
    // 验证奖品名称
    if (!name || name.trim() === '') {
        alert('请输入奖品名称！');
        return false;
    }

    // 如果奖品名称被修改了，则检查是否与其他奖品重复
    if (name.trim() !== originalName && isPrizeDuplicate(name.trim())) {
        alert('该奖品已存在，请更换奖品名称！');
        return false;
    }

    // 验证奖品数量
    if (!count || isNaN(count) || parseInt(count) <= 0) {
        alert('奖品数量必须大于0！');
        return false;
    }

    return true;
}

// 验证发言参与设置
function validateMessageSettings(messageCount, checkTime) {
    if (!messageCount || messageCount < 1) {
        alert('请设置有效的发言条数要求（至少1条）');
        return false;
    }
    
    if (!checkTime || checkTime < 1 || checkTime > 24) {
        alert('请设置有效的检查时间范围（1-24小时）');
        return false;
    }
    
    return true;
}

// 添加实时验证的事件监听器
document.addEventListener('DOMContentLoaded', function() {
    const messageCountInput = document.getElementById('message-count');
    const messageCheckTimeInput = document.getElementById('message-check-time');

    // 发言条数实时验证
    if (messageCountInput) {
        messageCountInput.addEventListener('input', function() {
            let value = parseInt(this.value);
            if (isNaN(value) || value < 1) {
                this.value = 1;
            }
        });
    }

    // 检查时间范围实时验证
    if (messageCheckTimeInput) {
        messageCheckTimeInput.addEventListener('input', function() {
            let value = parseInt(this.value);
            if (isNaN(value) || value < 1) {
                this.value = 1;
            } else if (value > 24) {
                this.value = 24;
            }
        });
    }
});
