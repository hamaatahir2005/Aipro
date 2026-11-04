allprojects { repositories { google(); mavenCentral() } }
rootProject.layout.buildDirectory.set(file("../build"))
subprojects { layout.buildDirectory.set(rootProject.layout.buildDirectory.dir(project.name)) }
tasks.register<Delete>("clean") { delete(rootProject.layout.buildDirectory) }
