Name:		javac-parse
Version:	0.9.0
Release:	1
Summary:	Wrapper around javac's parser
Group:		Development/Java
License:	GPL-2.0-only WITH Classpath-exception-2.0
URL:		https://github.com/plume-lib/javac-parse
# Tag v0.9.0, Java sources only. The Gradle wrapper jar is not in this archive.
Source0:	javac-parse-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(org.checkerframework:checker-qual) = 4.4.0

%description
javac-parse %{version} calls the JDK javac parser and returns a tree.
Checker Framework dataflow uses it to parse Java expressions.
--release hides com.sun.tools.javac, so these classes match the JDK that
built them. GuardSatisfied comes from checker-qual and is compile-only.

A caller in the unnamed module needs:
--add-exports=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED
--add-exports=jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED

%prep
%autosetup -n javac-parse-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
find src/main/java -name '*.java' > sources.list
test "$(wc -l < sources.list)" -eq 5
mkdir -p classes
javac -encoding UTF-8 -Xlint:all,-processing,-options,-this-escape,-removal -Werror -proc:none \
	--add-exports=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED \
	--add-exports=jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED \
	--add-exports=jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED \
	--add-exports=jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED \
	--add-exports=jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED \
	--add-exports=jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED \
	-cp %{_javadir}/checker-qual.jar \
	-d classes @sources.list
echo 'Automatic-Module-Name: org.plumelib.javacparse' > javac-parse.mf
jar cfm javac-parse.jar javac-parse.mf -C classes .
jar i javac-parse.jar
javap -v -classpath javac-parse.jar org.plumelib.javacparse.JavacParse | grep -F -q 'major version: 71'
desc=$(jar --describe-module --file javac-parse.jar)
printf '%s\n' "$desc" | grep -F -q 'org.plumelib.javacparse'
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	exit 1
fi

cat > javac-parse.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.plumelib</groupId>
  <artifactId>javac-parse</artifactId>
  <version>%{version}</version>
  <name>javac-parse</name>
  <description>Wrapper around javac's parser, used by Checker Framework dataflow.</description>
  <url>https://github.com/plume-lib/javac-parse</url>
  <licenses>
    <license>
      <name>GPL-2.0-only WITH Classpath-exception-2.0</name>
      <url>https://www.gnu.org/licenses/old-licenses/gpl-2.0.html</url>
      <distribution>repo</distribution>
    </license>
  </licenses>
</project>
END

%install
sysjar install --buildroot %{buildroot} \
	--artifact javac-parse.pom:javac-parse.jar \
	--file-name javac-parse \
	--filelist .mfiles

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
mkdir -p check
cat > check/Smoke.java << 'EOF'
import com.sun.source.tree.BinaryTree;
import com.sun.source.tree.ExpressionTree;
import com.sun.source.tree.LiteralTree;
import org.plumelib.javacparse.JavacParse;
import org.plumelib.javacparse.JavacParseResult;

public class Smoke {
	public static void main(String[] args) {
		JavacParseResult<ExpressionTree> parsed = JavacParse.parseExpression(args[1]);
		if (parsed.hasParseError()) {
			throw new AssertionError(parsed.getParseErrorMessages());
		}
		ExpressionTree tree = parsed.getTree();
		if (!(tree instanceof BinaryTree)) {
			throw new AssertionError(tree.getKind());
		}
		BinaryTree binary = (BinaryTree) tree;
		String left = ((LiteralTree) binary.getLeftOperand()).getValue().toString();
		String right = ((LiteralTree) binary.getRightOperand()).getValue().toString();
		System.out.println(args[0] + " " + left + " " + binary.getKind() + " " + right);
	}
}
EOF
JAR=%{buildroot}%{_javadir}/javac-parse.jar
test -s "$JAR"
EXPORTS="--add-exports=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED --add-exports=jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED"
javac -encoding UTF-8 -proc:none $EXPORTS -cp "$JAR" -d check check/Smoke.java
java $EXPORTS -cp "check:$JAR" Smoke javacparse_ok '1 + 2' > check/out.txt
cat check/out.txt
grep -F -q 'javacparse_ok 1 PLUS 2' check/out.txt

%files -f .mfiles
%doc README.md CHANGELOG.md
%license LICENSE
