# PFM
MySQLScheduler.py is the shell for the program. You call it with a config file that has your database info.
The script calls the database and builds the squadron model. Once the squadron model is built, it calls the squadron scheduling function.
That function constructs the Gurobi LP and optimizes the model. It writes the optimal schedules to schedules objects in the squadron model.
MySQLScheduler then takes the squadron object with schedules and write them to the database, deleting the past entries.
