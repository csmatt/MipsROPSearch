import re

register_list_through_pattern = re.compile(r'([a-z])([0-9])\-[a-z]([0-9])')
register_list_all_group_pattern = re.compile(r'([a-z])\*')
register_list_single_pattern = re.compile(r'([a-z0-9]{2})')


def build_register_list_from_pattern(register_list_pattern):
    """returns a list of register names created by expanding expressions defining one or more register names"""
    register_list_parts = register_list_pattern.split(',')
    register_list = []
    for part in register_list_parts:
        if register_list_through_pattern.match(part):
            reg_group, reg_num_from, reg_num_to = register_list_through_pattern.findall(part)[0]
            for reg_num in xrange(int(reg_num_from), int(reg_num_to)+1):
                register_list.append("%s%s" % (reg_group, reg_num))
        elif register_list_all_group_pattern.match(part):
            reg_group = register_list_all_group_pattern.findall(part)[0]
            for reg_num in xrange(0, 10):
                register_list.append("%s%s" % (reg_group, reg_num))
        elif register_list_single_pattern.match(part):
            register_list.append(register_list_single_pattern.findall(part)[0])
    return register_list


def print_list(l, depth=0, last_was_list=False):
    """recursively prints contents of lists of lists"""
    if type(l) == list:
        for i in l:
            print_list(i, depth+1, True)
        if last_was_list:
            print ""
    else:
        print "%s%s" % ("\t"*depth, l)