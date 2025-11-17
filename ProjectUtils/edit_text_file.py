import shutil, os

def replace_line_in_file(file_path, line_number, new_line):
    with open(file_path, 'r') as file:
        lines = file.readlines()  

    if 0 <= line_number < len(lines):
        lines[line_number] = new_line + '\n' 

        # Write the modified lines back to the file
        with open(file_path, 'w') as file:
            file.writelines(lines)
    else:
        print(f"Invalid line number: {line_number}")
        
def create_dat_general(parameters, jobid):
    #create and edit alignment parameters text file to add to CLAS12 ccdb.
    # assume parameters named as "{param}_{layer}_{component}".
    # component == 0 is mis-alignment applied to full layer    
    line_number_dict = {"201":2,
                        "202":19,
                        "203":42,"204":75,
                        "301":{"1":108,"2":109,
                               "3":110, "4":111,
                               "5":112, "6":113,
                               "7":114},
                        "302":{
                            "1":116,"2":117,
                            "3":118,"4":119,
                            "5":120,"6":121,
                            "7":122,"8":123,
                            "9":124,"10":125,
                            },
                        "global":1
                        }
    
    dat_init = str(os.environ["AIDE_HOME"])+"/rich/tables/rich_m1_alignment_bestglobal_frommarco.dat"
    dat_job = str(os.environ["AIDE_HOME"])+"/rich/tables/rich_m1_alignment_{}.dat".format(jobid)
    shutil.copyfile(dat_init, dat_job)

    keys = parameters.keys()
    if any("201" in k for k in keys):
        # same for 201 and planar mirror 2
        line_number = line_number_dict["201"]
        new_line = f"  4            201          0            0    0    {parameters['dz_201_0']}    {parameters['dthx_201_0']}    {parameters['dthy_201_0']}     0"
        replace_line_in_file(dat_job, line_number, new_line)
        # matching planar
        line_number = line_number_dict["301"]["2"]
        new_line = f"  4            301          2            0    0    {parameters['dz_201_0']}    {parameters['dthx_201_0']}    {parameters['dthy_201_0']}     0"
        replace_line_in_file(dat_job, line_number, new_line)
    if any("202" in k for k in keys):
        # same for 202 and planar mirror 3
        line_number = line_number_dict["202"]
        new_line = f"  4            202          0            0    0    {parameters['dz_202_0']}    {parameters['dthx_202_0']}    {parameters['dthy_202_0']}     0"
        replace_line_in_file(dat_job, line_number, new_line)
        # matching planar
        line_number = line_number_dict["301"]["3"]
        new_line = f"  4            301          3            0    0    {parameters['dz_202_0']}    {parameters['dthx_202_0']}    {parameters['dthy_202_0']}     0"
        replace_line_in_file(dat_job, line_number, new_line)
    if any("203" in k for k in keys):
        # same for 203 and 204
        line_number = line_number_dict["203"]
        new_line = f"  4            203          0            0    0    {parameters['dz_203_0']}    {parameters['dthx_203_0']}    {parameters['dthy_203_0']}     0"
        replace_line_in_file(dat_job, line_number, new_line)
        line_number = line_number_dict["204"]
        new_line = f"  4            204          0            0    0    {parameters['dz_203_0']}    {parameters['dthx_203_0']}    {parameters['dthy_203_0']}     0"
        replace_line_in_file(dat_job, line_number, new_line)
    if any("global" in k for k in keys):
        line_number = line_number_dict["global"]
        if any("dthy_global" in k for k in keys):
            # if constraining global angles
            new_line = f"  4            0            0            {parameters['dx_global_0']}    {parameters['dy_global_0']}    {parameters['dz_global_0']}    {parameters['dthx_global_0']}    {parameters['dthy_global_0']}    {parameters['dthz_global_0']}"
        else:
            # otherwise assume only shifts
            new_line = f"  4            0            0            {parameters['dx_global_0']}    {parameters['dy_global_0']}    {parameters['dz_global_0']}    0    0    0"
        replace_line_in_file(dat_job, line_number, new_line)
    # loop over mirrors
    for i in range(1, 8):
        key = f"301_{i}"
        if any(key in k for k in keys):
            line_num = line_number_dict["301"][str(i)]
            new_line = (
                f"  4            301          {i}            0    0    "
                f"{parameters[f'dz_301_{i}']}    "
                f"{parameters[f'dthx_301_{i}']}    "
                f"{parameters[f'dthy_301_{i}']}     0"
            )
            replace_line_in_file(dat_job, line_num, new_line)
    for i in range(2, 11): #TODO TODO TODO: set back to (1,11) after upper...
        key = f"302_{i}"
        if any(key in k for k in keys):
            line_num = line_number_dict["302"][str(i)]
            new_line = (
                f"  4            302          {i}            0    0    "
                f"{parameters[f'dz_302_{i}']}    "
                f"{parameters[f'dthx_302_{i}']}    "
                f"{parameters[f'dthy_302_{i}']}     0"
            )
            replace_line_in_file(dat_job, line_num, new_line)
            
    return
def create_yaml(jobid):
    #create and edit yaml file                                                                                                      
    yaml_init = str(os.environ["AIDE_HOME"])+"/rich/yaml/rich.yaml"
    yaml_job = str(os.environ["AIDE_HOME"])+"/rich/yaml/rich_{}.yaml".format(jobid)
    shutil.copyfile(yaml_init, yaml_job)
    
    line_number_yaml = 10#11 #old yaml
    new_line_yaml = str('      variation: variation_{}'.format(jobid))

    replace_line_in_file(yaml_job, line_number_yaml, new_line_yaml)

    return
