// validation.js
function validateForm(event) {
    console.log('开始验证表单');
    console.log('事件对象:', event); // 输出事件对象
    // 抽奖标题验证
    const title = document.getElementById('title').value;
    if (!title) {
        alert('请输入抽奖标题！');
        console.log('验证未通过：未输入抽奖标题，返回 false');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        console.log('返回值:', false); // 输出返回值
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
        console.log('验证未通过：未输入图片或视频链接，返回 false');
        alert('请输入图片或视频链接！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        console.log('返回值:', false); // 输出返回值
        return false;
    }

    // 抽奖文字说明验证
    const descriptionEditor = new Quill('#description-editor');
    const description = descriptionEditor.root.innerHTML;
    if (!description || description === '<p><br></p>') {
        console.log('验证未通过：未输入抽奖文字说明，返回 false');
        alert('请输入抽奖文字说明！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        console.log('返回值:', false); // 输出返回值
        return false;
    }

    // 请选关键词群组选择框验证
    const joinMethod = document.querySelector('input[name="join_method"]:checked').value;
    if (joinMethod === 'send_keywords_in_group') {
        const keywordGroup = document.getElementById('keyword-group').value;
        if (!keywordGroup) {
            console.log('验证未通过：未选择关键词群组，返回 false');
            alert('请选择关键词群组！');
            if (event) {
                event.preventDefault();
                event.stopPropagation(); // 阻止事件冒泡
            }
            console.log('返回值:', false); // 输出返回值
            return false;
        }
        // 抽奖关键词输入框验证
        const lotteryKeyword = document.getElementById('lottery-keyword').value;
        if (!lotteryKeyword) {
            console.log('验证未通过：未输入抽奖关键词，返回 false');
            alert('请输入抽奖关键词！');
            if (event) {
                event.preventDefault();
                event.stopPropagation(); // 阻止事件冒泡
            }
            console.log('返回值:', false); // 输出返回值
            return false;
        }
    }

    // 需要成员加入的群或频道列表验证
    const groupTableBody = document.getElementById('group-table-body');
    const groupRows = groupTableBody.getElementsByTagName('tr');
    if (groupRows.length === 0) {
        console.log('验证未通过：未选择需要成员加入的群或频道，返回 false');
        alert('请添加需要成员加入的群或频道！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        console.log('返回值:', false); // 输出返回值
        return false;
    }

    // 根据开奖方式进行验证
    const drawMethod = document.querySelector('input[name="draw_method"]:checked').value;
    if (drawMethod === 'draw_when_full') {
        // 满人开奖时验证参与人数
        const participantCount = document.getElementById('participant-count').value;
        if (!participantCount || isNaN(participantCount) || parseInt(participantCount) <= 0) {
            console.log('验证未通过：参与人数输入不合法，返回 false');
            alert('参与人数必须大于 0！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            console.log('返回值:', false);
            return false;
        }
    } else if (drawMethod === 'draw_at_time') {
        // 定时开奖时验证开奖日期
        const drawDate = document.getElementById('draw-date').value;
        if (!drawDate) {
            console.log('验证未通过：未选择开奖日期，返回 false');
            alert('请选择开奖日期！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            console.log('返回值:', false);
            return false;
        }
        const now = new Date();
        const selectedDate = new Date(drawDate);
        if (selectedDate <= now) {
            console.log('验证未通过：选择的开奖日期不能是过去的时间，返回 false');
            alert('开奖日期不能选择过去的时间！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            console.log('返回值:', false);
            return false;
        }
    }

    // 奖品列表验证
    const prizeTableBody = document.getElementById('prize-table-body');
    const prizeRows = prizeTableBody.getElementsByTagName('tr');
    if (prizeRows.length === 0) {
        console.log('验证未通过：未设置奖品，返回 false');
        alert('请设置奖品！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        console.log('返回值:', false); // 输出返回值
        return false;
    }
    console.log('验证通过，返回 true');
    console.log('返回值:', true); // 输出返回值
    return true;

}


function validateAddPrize() {
    // 奖品名称输入框验证
    const prizeName = document.getElementById('prize-name').value;
    if (!prizeName) {
        alert('请输入奖品名称！');
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

// 添加验证函数
function validatePrize(name, count) {
    // 验证奖品名称
    if (!name || name.trim() === '') {
        alert('奖品名称为必填项');
        return false;
    }

    // 验证奖品数量
    if (!count || isNaN(count) || parseInt(count) <= 0) {
        alert('奖品数量必须为大于0的整数');
        return false;
    }

    return true;
}